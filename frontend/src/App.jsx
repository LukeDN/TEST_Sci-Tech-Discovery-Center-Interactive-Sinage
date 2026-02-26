import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import LangaugeSelect from './components/langaugeSelect';
import VideoScreen from './components/videoScreen';
import ScanPage from './components/ScanPage';

function SSEController() {
  const navigate = useNavigate();
  const [connectionState, setConnectionState] = useState(0); // 0: connecting, 1: open

  function waitForEventSourceOpen(eventSource) {
    if (eventSource.readyState === 1) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const openListener = () => {
        eventSource.removeEventListener('open', openListener);
        eventSource.removeEventListener('error', errorListener);
        resolve();
      }
      const errorListener = (err) => {
        eventSource.removeEventListener('open', openListener);
        eventSource.removeEventListener('error', errorListener);
        console.log(err)
        reject(new Error("Error establishing EventSource connection"));
      }
      eventSource.addEventListener('open', openListener);
      eventSource.addEventListener('error', errorListener);
    })
  };

  useEffect(() => {
    console.log("Setting up EventSource connection...");
    const eventSource = new EventSource('/api/events/');

    async function openConnection() {
      await waitForEventSourceOpen(eventSource);
      setConnectionState(1);
      console.log("EventSource connection established.");

    }
    openConnection()



    // Map event types directly to routes
    const eventTypeMap = {
      'scanned_id': '/exploration',
      'button_press': '/video',
      'button_press_timeout': '/video'
    };

    // Event listeners
    eventSource.addEventListener('scanned_id', (event) => {
      const data = JSON.parse(event.data);
      console.log("Received scanned_id event:", data);
      const targetPath = eventTypeMap['scanned_id'];
      navigate(targetPath, { state: data });
    });

    eventSource.addEventListener('button_press', (event) => {
      const data = JSON.parse(event.data);
      console.log("Received button_press event:", data);
      const targetPath = eventTypeMap['button_press'];
      navigate(targetPath, { state: { lang: data["language"] } });
    });

    eventSource.addEventListener('button_press_timeout', (event) => {
      const data = JSON.parse(event.data);
      console.log("Received button_press_timeout event:", data);
      const targetPath = eventTypeMap['button_press_timeout'];
      navigate(targetPath, { state: { lang: data["language"] } });
    });

    // Cleanup
    return () => {
      console.log("Closing EventSource connection...");
      eventSource.close();
    };
  }, [navigate]);

  // This component renders nothing
  return (
    connectionState === 0 ? <div className="w-full h-screen bg-black flex items-center justify-center text-white">Loading....</div> : null

  );
}

// 2. Main App Component
function App() {

  return (
    <main>
      <BrowserRouter>

        <SSEController />




        <Routes>
          <Route path="/" element={<ScanPage />} />
          <Route path="/exploration" element={<LangaugeSelect />} />
          <Route path="/video" element={<VideoScreen />} />
        </Routes>
      </BrowserRouter>
    </main>
  );
}

export default App;