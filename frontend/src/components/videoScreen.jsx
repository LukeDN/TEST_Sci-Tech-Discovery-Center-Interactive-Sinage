import React from "react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import sampleVideo from "../assets/video.mp4";
import testdata from "../assets/testdata.json";

export default function VideoScreen({ lang }) {
  const [videoData, setVideoData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    console.log("Running useEffect to fetch ShowInfo data...");

    const url = `/api/showinfo/`;

    fetch(url, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
      }
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        if (data.error) {
          console.log("Error in ShowInfo", data.error);
          // Redirect back to scan page on error
          console.log("Redirecting to scan page due to error...");
          navigate('/');
        } else {
          console.log("ShowInfo Data:", data);
          setVideoData(data);
        }
      })
      .catch(err => {
        console.log(err.message);
        // Redirect back to scan page on fetch error
        console.log("Redirecting to scan page due to fetch error...");
        navigate('/');
      });
  }, [navigate]);

  const handleVideoEnd = async () => {
    console.log("Video finished. Reseting Flags...");

    try {
      await fetch("/api/resetinfo/");
      console.log("Flags reset successfully");
    } catch (error) {
      console.error("Error resetting flags:", error);
    }


    //Switch to the next screen
    console.log("Request sent. Switching screens.");
    navigate('/');


  };
  if (!videoData || !videoData.video_path) {
    console.log(videoData);
    return <div className="w-full h-screen bg-black flex items-center justify-center text-white">Loading Video...</div>;
  }
  const path = videoData ? videoData.video_path : "No Video Path Retrieved From Showinfo API";
  console.log("Video Path:", path);

  return (
    <div className="w-full h-screen flex items-center justify-center bg-black">
      <video
        src={path}
        controls
        muted
        autoPlay
        onEnded={handleVideoEnd}
        playsInline
        poster="/src/assets/video-poster.jpg"
        className="w-full h-full rounded-2xl shadow-lg object-cover"
      />
    </div>
  );
}