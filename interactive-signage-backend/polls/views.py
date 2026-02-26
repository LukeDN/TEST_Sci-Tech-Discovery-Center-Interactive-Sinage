from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from .getpath import getpath
import time
import queue
import threading

BUTTON_RECEIVED_ONCE = False    # Flag to track if a button has been received
ID_RECEIVED_ONCE = False        # Flag to track if a denary ID has been received 
CURRENT_DEN_ID = None           # Placeholder for the current denary ID
CURRENT_BUTTON = None           # Placeholder for the current button state
TIMEOUT_SECONDS = 15             # Timeout duration in seconds

# SSE event queue and timer
# SSE event queue management
# We use a set of queues to support broadcasting to multiple clients (e.g. multiple tabs)
active_queues = set()
active_queues_lock = threading.Lock()

active_timer = None             # global reference to cancel timers
default_language = "en"

# Helper to broadcast event to all connected clients
def broadcast_event(data):
    with active_queues_lock:
        for q in active_queues:
            q.put(data)

# Timeout handler - triggers when no button is pressed within timeout period
def trigger_timeout():
    global CURRENT_BUTTON, BUTTON_RECEIVED_ONCE
    
    # Set default language to English
    CURRENT_BUTTON = "en"
    BUTTON_RECEIVED_ONCE = True
    
    default_language = CURRENT_BUTTON
    # Send auto-timeout button press event
    broadcast_event({"type": "button_press_timeout", "language": default_language})


#Endpoint to show info based on current denary ID and button
def showinfo(request):
    global CURRENT_DEN_ID, CURRENT_BUTTON, ID_RECEIVED_ONCE, BUTTON_RECEIVED_ONCE

    # Rejects request if ID has not been received yet
    if not ID_RECEIVED_ONCE:
        return JsonResponse({"error": "No denary ID received yet"}, status=400)

    # Rejects request if button has not been received yet
    if not BUTTON_RECEIVED_ONCE:
        return JsonResponse({"error": "No button press received yet"}, status=400)
    
    data = getpath(CURRENT_DEN_ID, CURRENT_BUTTON)

    status = 404 if "error" in data else 200
    
    return JsonResponse(data, status=status)


            
#Endpoint to receive and set denary ID
def receive_den_id(request):
    global ID_RECEIVED_ONCE, CURRENT_DEN_ID, active_timer
    
    if ID_RECEIVED_ONCE:
        return JsonResponse({"error": f"ID {CURRENT_DEN_ID} already received. No more requests till reset"}, status=200)
    
    denary_id = request.GET.get("id")

    if not denary_id:
        return JsonResponse({"error": "Missing id parameter"}, status=400)

    # Validate ID exists in database
    data = getpath(denary_id)

    if "error" in data:
        return JsonResponse({"error": "Invalid ID - not found in database"}, status=404)

    # Store the ID
    CURRENT_DEN_ID = denary_id 
    ID_RECEIVED_ONCE = True
    
    # Send scanned_id event immediately
    broadcast_event({"type": "scanned_id", "path": data["video_path"]})

    # Cancel any existing timer
    if active_timer and active_timer.is_alive():
        active_timer.cancel()

    # Start new timeout that triggers default button press after 5 seconds
    active_timer = threading.Timer(TIMEOUT_SECONDS, trigger_timeout)
    active_timer.start()

    return JsonResponse({"OK": f"Successful. ID set to {CURRENT_DEN_ID}"}, status=200)


#Endpoint to receive button press
def receive_button_press(request):
    global BUTTON_RECEIVED_ONCE, CURRENT_BUTTON, ID_RECEIVED_ONCE, active_timer

    if active_timer and active_timer.is_alive():
        active_timer.cancel()
 
    # Validate sequential flow
    if not ID_RECEIVED_ONCE:
        return JsonResponse({"error": "No denary ID received yet. Cannot process button press."}, status=400)
    
    # Check if button already received
    if BUTTON_RECEIVED_ONCE:
        return JsonResponse({"error": f"Button {CURRENT_BUTTON} already received. No more requests till reset"}, status=200)

    # Get button parameter
    button = request.GET.get("button")

    if not button:
        return JsonResponse({"error": "Missing button parameter"}, status=400)
    
    # Validate button parameter
    if button not in ["a", "b", "c"]:
        return JsonResponse({"error": "Invalid button parameter"}, status=400)
    
    # Cancel the timeout timer since user pressed a button
    if active_timer and active_timer.is_alive():
        active_timer.cancel()
    
    # Map button to language
    button_map = {"a": "en", "b": "es", "c": "te"}
    language = button_map[button]

    # Store button and set flag
    CURRENT_BUTTON = language
    BUTTON_RECEIVED_ONCE = True
    
    # Send button_press event to Frontend
    broadcast_event({"type": "button_press", "language": language})


    return JsonResponse({"OK": f"Button press validated and stored. Language set to {CURRENT_BUTTON}"}, status=200)



#Endpoint to reset all globals and clean up timer; 
def restartflag(request):
    global BUTTON_RECEIVED_ONCE, ID_RECEIVED_ONCE, CURRENT_BUTTON, CURRENT_DEN_ID, active_timer

    # Cancel any active timer ; good for house keeping
    if active_timer and active_timer.is_alive():
        active_timer.cancel()

    # Reset all globals to initial state when cycle is complete
    BUTTON_RECEIVED_ONCE = False
    ID_RECEIVED_ONCE = False
    CURRENT_DEN_ID = None 
    CURRENT_BUTTON = None 
    active_timer = None
    
    return JsonResponse({"OK": "Flags reset successfully"}, status=200)


# SSE endpoint needed to subscribe to events; Queue structure to store events
def sse_events(request):
    def event_stream():
        # Create a queue for this specific connection
        q = queue.Queue()
        with active_queues_lock:
            active_queues.add(q)
            
        try:
            while True:
                try:
                    event = q.get(timeout=30)
                    if event["type"] == "scanned_id":
                        yield f'event: scanned_id\ndata: {{"path": "{event["path"]}"}}\n\n'
                    elif event["type"] == "button_press_timeout":
                        #for timeout button press
                        yield f'event: button_press_timeout\ndata: {{ "language": "{event["language"]}"}}\n\n'
                    elif event["type"] == "button_press":
                        #for normal button press
                        yield f'event: button_press\ndata: {{ "language": "{event["language"]}"}}\n\n'
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield "data: heartbeat\n\n"
        finally:
            # Clean up when connection closes
            with active_queues_lock:
                active_queues.discard(q)


    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    #http headers 
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering for nginx
    return response