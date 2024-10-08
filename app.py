from flask import Flask, jsonify
from script import main  # Import your main function from the script
import gc

app = Flask(__name__)

@app.route('/trigger', methods=['GET'])
def trigger_script():
    try:
        res=main()  # Call the main function from your script
        
        gc.collect()
        return jsonify({'status': 'success', 'message': f'{res[0]}', 'Last runing time':f'{res[1]}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
