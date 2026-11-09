import os
import uvicorn
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting StudyBuddy on http://0.0.0.0:{port}")
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')