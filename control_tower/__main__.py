import argparse
import uvicorn
from .api import create_app

parser=argparse.ArgumentParser(description='Local synthetic AgentGuard Control Tower; no real financial operations.')
parser.add_argument('--port',type=int,default=8010)
parser.add_argument('--data',default='local-data/control-tower.sqlite')
parser.add_argument('--live',action='store_true',help='Explicitly enable Meta; requires server key, activation and existing RequestGuard allowance.')
args=parser.parse_args()
uvicorn.run(create_app(args.data,live=args.live),host='127.0.0.1',port=args.port,workers=1)
