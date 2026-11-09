import os, sys
sys.path.insert(0, '/home/makkusu/.hermes/installs/6ca0a94937694e70/environments/52684fa3ab224892a97b3b9dfa12d399/venv/lib/python3.14/site-packages')

os.environ['LLM_BASE'] = 'http://localhost:3001/v1'
os.environ['LLM_KEY']  = 'freellmapi-658cd66399606328ed1c4158055a64909ee449bc388fa661'
os.environ['PORT']     = '8000'

from app import app

if __name__ == '__main__':
    import uvicorn
    print("Starting StudyBuddy on http://0.0.0.0:8000")
    print("LAN URL: http://192.168.100.32:8000")
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')