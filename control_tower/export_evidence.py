"""Read-only export of allowlisted evidence; no database initialisation or API calls."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3

from .agent import SCENARIOS
from .evidence import digest

SCENARIO_NAMES=('automatic_125','human_approval_300','hard_denial_750','clarification')
EXPECTED=('SUCCEEDED','SUCCEEDED','DENIED','CLARIFICATION_REQUIRED')
KINDS=('workflow_created','model_call','proposal_validated','policy_evaluated','human_approved',
       'execution_started','tool_executed','execution_denied','proposal_failed','interruption_detected',
       'recovery_requested','receipt_reconciled','demo_checkpoint')
STATES={'SUCCEEDED','DENIED','AWAITING_APPROVAL','CLARIFICATION_REQUIRED','FAILED','INTERRUPTED','INTERPRETING','READY','EXECUTING'}


def chain_valid(events):
    previous='0'*64
    for event,saved_hash in events:
        if event.get('previous_hash')!=previous or digest(event)!=saved_hash:
            return False
        previous=saved_hash
    return bool(events)


def export_report(source):
    source=Path(source).resolve()
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')  # One consistent read snapshot across every table.
        rows=[]
        source_rows=[(wid,json.loads(payload)) for wid,payload in db.execute('SELECT id,payload FROM workflows')]
        source_rows.sort(key=lambda row:(str(row[1].get('created_at','')),row[0]))
        for ordinal,(wid,w) in enumerate(source_rows,1):
            events=[(json.loads(raw),sha) for raw,sha in db.execute('SELECT payload,hash FROM events WHERE workflow_id=? ORDER BY seq',(wid,))]
            kinds=Counter(e['kind'] for e,_ in events)
            created=[e['detail'] for e,_ in events if e['kind']=='workflow_created']
            proposals=[e['detail'] for e,_ in events if e['kind']=='proposal_validated']
            bound=bool(created) and created[0].get('customer_text')==w.get('text') and created[0].get('mode')==w.get('mode')
            if w.get('proposal') is not None:
                bound=bound and bool(proposals) and proposals[-1]==w['proposal']
            valid=chain_valid(events) and bound
            scenario=next((i for i,s in enumerate(SCENARIOS) if s['text']==w.get('text')),None)
            receipts=list(db.execute('SELECT transaction_id,amount_cents FROM receipts WHERE workflow_id=?',(wid,)))
            tools=[e['detail'] for e,_ in events if e['kind']=='tool_executed']
            policies=[e['detail'] for e,_ in events if e['kind']=='policy_evaluated']
            calls=[]
            for event,_ in events:
                if event['kind']!='model_call': continue
                detail=event['detail'];usage={}
                reported=detail.get('reported_usage')
                if isinstance(reported,dict):
                    usage={key:value for key,value in reported.items() if key in ('input_tokens','output_tokens','total_tokens') and type(value) is int and value>=0}
                duration=detail.get('duration_ms')
                if type(duration) not in (int,float) or not math.isfinite(duration) or duration<0: duration=None
                outcome=detail.get('outcome')
                calls.append({'outcome':outcome if outcome in ('completed','blocked','provider_failed') else 'unknown','duration_ms':duration,'reported_usage':usage})
            outcome_ok=scenario is not None and w.get('status')==EXPECTED[scenario]
            policy_ok=False
            if scenario in (0,1):
                amount=(12500,30000)[scenario];tx=('DEMO-125','DEMO-300')[scenario]
                policy_ok=(len(receipts)==len(tools)==1 and receipts[0]==(tx,amount)
                           and tools[0].get('transaction_id')==tx and tools[0].get('amount_cents')==amount
                           and tools[0].get('tool')=='simulate_refund' and tools[0].get('simulated') is True
                           and any(p.get('outcome')==('READY' if scenario==0 else 'AWAITING_APPROVAL') for p in policies))
                if scenario==1:
                    order=[e['kind'] for e,_ in events]
                    policy_ok=policy_ok and kinds['human_approved']==1 and w.get('approved') is True and order.index('human_approved')<order.index('tool_executed')
            elif scenario in (2,3):
                policy_ok=(not receipts and not tools and not kinds['execution_started'] and not kinds['human_approved']
                           and any(p.get('outcome')==EXPECTED[scenario] for p in policies))
            passed=bool(valid and outcome_ok and policy_ok and w.get('mode')=='meta' and len(calls)==1 and calls[0]['outcome']=='completed')
            rows.append({'record':ordinal,'scenario':SCENARIO_NAMES[scenario] if scenario is not None else 'other',
                         'mode':'meta' if w.get('mode')=='meta' else 'offline_or_unknown',
                         'status':w.get('status') if w.get('status') in STATES else 'unknown',
                         'evidence_verified':bool(valid),'expected_outcome_verified':passed,
                         'event_counts':{kind:kinds[kind] for kind in KINDS if kinds[kind]},
                         'receipt_count':len(receipts),'simulated_amount_eur':(receipts[0][1]/100 if passed and receipts else None),
                         'model_calls':calls,
                         'chain_head':events[-1][1] if valid else None})
        summary={name:any(row['scenario']==name and row['expected_outcome_verified'] for row in rows) for name in SCENARIO_NAMES}
    return {'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),
            'evidence_type':'recorded_live_workflows','complete':all(summary.values()),'scenario_checks':summary,'workflows':rows,
            'limitations':['No inference was performed during export.','Only the four exact scenario texts are classified; other rows are labelled other.',
                            'Raw text, proposals, reviewer labels, workflow IDs, credentials, raw errors and database paths are excluded.',
                            'Chains were verified against local source records. This sanitised summary cannot independently reconstruct them and is not externally signed.',
                            'One observed result per scenario does not establish broad language accuracy, production readiness or a dollar spending cap.',
                            'The original local workflow database remains excluded from Git.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('local-data/live-control-tower.sqlite'))
    parser.add_argument('--output',type=Path,default=Path('evidence/live-scenarios.json'))
    args=parser.parse_args()
    if args.source.resolve()==args.output.resolve():
        parser.exit(1,'Source and output must differ.\n')
    try:
        report=export_report(args.source)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as file:
            json.dump(report,file,indent=2,allow_nan=False)
            file.write('\n')
    except FileExistsError:
        parser.exit(1,'Output exists; choose a new output filename. Nothing overwritten.\n')
    except Exception:
        parser.exit(1,'Evidence could not be exported; no raw source details printed.\n')
    print('Recorded scenario checks:', 'PASS' if report['complete'] else 'INCOMPLETE')
    return 0 if report['complete'] else 1


if __name__=='__main__':
    raise SystemExit(main())
