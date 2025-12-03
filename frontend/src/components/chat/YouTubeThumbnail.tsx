import React from 'react';
import { Play } from 'lucide-react';

interface YouTubeThumbnailProps {
  videoId: string;
  timestamp?: number; // in seconds
  url: string;
}

/**
 * Formats seconds into MM:SS or HH:MM:SS format
 */
const formatTimestamp = (seconds: number): string => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Clickable YouTube thumbnail that opens the video at a specific timestamp
 */
const YouTubeThumbnail: React.FC<YouTubeThumbnailProps> = ({ videoId, timestamp, url }) => {
  // YouTube thumbnail URL (mqdefault is 320x180)
  const thumbnailUrl = `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-block my-2 group"
    >
      <div className="relative w-64 rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-shadow">
        {/* Thumbnail Image */}
        <img
          src={thumbnailUrl}
          alt="YouTube video thumbnail"
          className="w-full h-36 object-cover"
        />

        {/* Play Button Overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
          <div className="w-12 h-12 bg-red-600 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform">
            <Play className="w-6 h-6 text-white fill-white ml-1" />
          </div>
        </div>

        {/* Timestamp Badge */}
        {timestamp !== undefined && (
          <div className="absolute bottom-2 right-2 bg-black/80 text-white text-xs font-medium px-2 py-1 rounded">
            {formatTimestamp(timestamp)}
          </div>
        )}

        {/* YouTube branding */}
        <div className="absolute top-2 left-2 bg-red-600 text-white text-xs font-bold px-1.5 py-0.5 rounded">
          YouTube
        </div>
      </div>
    </a>
  );
};

export default YouTubeThumbnail;
