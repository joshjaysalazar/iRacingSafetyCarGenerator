from core.generator import GeneratorState

start_generator_text = "Start SC Generator"
stop_generator_text = "Stop SC Generator"

def generator_state_messages(play_icon, stop_icon):
    return {
        GeneratorState.STOPPED: {
            'btn_run_text': start_generator_text,
            'btn_run_icon': play_icon,
            'message': "Generator stopped.",
        },
        GeneratorState.CONNECTING_TO_IRACING: {
            'btn_run_text': stop_generator_text,
            'btn_run_icon': stop_icon,
            'message': "Connecting to iRacing...",
        },
        GeneratorState.CONNECTED: {
            'btn_run_text': stop_generator_text,
            'btn_run_icon': stop_icon,
            'message': "Connected to iRacing.",
        },
        GeneratorState.ERROR_CONNECTING: {
            'btn_run_text': start_generator_text,
            'btn_run_icon': play_icon,
            'message': "Error connecting to iRacing.",
        },
        GeneratorState.WAITING_FOR_RACE_SESSION: {
            'btn_run_text': stop_generator_text,
            'btn_run_icon': stop_icon,
            'message': "Connected to iRacing\nWaiting for race session...",
        },
        GeneratorState.WAITING_FOR_GREEN: {
            'btn_run_text': stop_generator_text,
            'btn_run_icon': stop_icon,
            'message': "Connected to iRacing\nWaiting for green flag...",
        },
        GeneratorState.MONITORING_FOR_INCIDENTS: {
            'btn_run_text': stop_generator_text,
            'btn_run_icon': stop_icon,
            'message': "Connected to iRacing\nGenerating safety cars...",
        },
        GeneratorState.SAFETY_CAR_DEPLOYED: {
            'btn_run_text': stop_generator_text,
            'btn_run_icon': stop_icon,
            'message': "Connected to iRacing\nSafety car deployed.",
        },
        GeneratorState.UNCAUGHT_EXCEPTION: {
            'btn_run_text': start_generator_text,
            'btn_run_icon': play_icon,
            'message': "Generator threw uncaught exception,\nmore details in log.",
        },
    }

def is_stopped_state(state):
    return state in [
        GeneratorState.STOPPED,
        GeneratorState.ERROR_CONNECTING,
        GeneratorState.UNCAUGHT_EXCEPTION,
    ] 