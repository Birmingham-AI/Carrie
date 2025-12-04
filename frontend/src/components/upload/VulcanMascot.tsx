import React from 'react';

export type MascotState = 'idle' | 'typing' | 'error' | 'success';

interface VulcanMascotProps {
  state: MascotState;
}

const VulcanMascot: React.FC<VulcanMascotProps> = ({ state }) => {
  const isTyping = state === 'typing';
  const isError = state === 'error';
  const isSuccess = state === 'success';

  const bronzeMain = '#CD7F32';
  const bronzeDark = '#8B5A2B';

  return (
    <div className={`relative w-40 h-48 ${isError ? 'animate-shake' : ''} ${isSuccess ? 'animate-bounce' : ''}`}>
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-5px); }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-4px); }
          75% { transform: translateX(4px); }
        }
        @keyframes sparkle {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .animate-float { animation: float 3s ease-in-out infinite; }
        .animate-shake { animation: shake 0.5s ease-in-out; }
        .animate-sparkle { animation: sparkle 0.3s ease-in-out infinite; }
      `}</style>

      <svg
        viewBox="-5 -15 135 175"
        className={`w-full h-full ${state === 'idle' ? 'animate-float' : ''}`}
      >
        {/* Stone Pedestal */}
        <rect x="25" y="135" width="70" height="12" rx="2" fill="#6B7280" />
        <rect x="30" y="128" width="60" height="10" rx="2" fill="#9CA3AF" />
        <rect x="35" y="122" width="50" height="8" rx="1" fill="#78716C" />

        {/* Legs */}
        <path d="M42 100 L38 122 L50 122 L52 100" fill={bronzeMain} />
        <path d="M68 100 L66 122 L78 122 L82 100" fill={bronzeMain} />
        <path d="M44 105 L44 118" stroke={bronzeDark} strokeWidth="2" />
        <path d="M72 105 L72 118" stroke={bronzeDark} strokeWidth="2" />

        {/* Apron */}
        <path d="M38 68 L35 105 Q60 112 85 105 L82 68 Q60 72 38 68" fill="#5C4033" />
        <path d="M50 75 L48 100" stroke="#3D2817" strokeWidth="2" fill="none" />
        <path d="M70 75 L72 100" stroke="#3D2817" strokeWidth="2" fill="none" />
        <path d="M38 70 Q60 75 82 70" stroke="#8B4513" strokeWidth="3" fill="none" />

        {/* Torso */}
        <ellipse cx="60" cy="58" rx="25" ry="20" fill={bronzeMain} />
        <path d="M45 52 Q52 58 50 62" stroke={bronzeDark} strokeWidth="2" fill="none" />
        <path d="M75 52 Q68 58 70 62" stroke={bronzeDark} strokeWidth="2" fill="none" />
        <path d="M60 48 L60 65" stroke={bronzeDark} strokeWidth="1" fill="none" />
        <path d="M55 65 Q60 67 65 65" stroke={bronzeDark} strokeWidth="1" fill="none" />

        {/* Shoulders */}
        <ellipse cx="35" cy="52" rx="12" ry="8" fill={bronzeMain} />
        <ellipse cx="85" cy="52" rx="12" ry="8" fill={bronzeMain} />

        {/* Neck */}
        <rect x="52" y="32" width="16" height="14" rx="3" fill={bronzeMain} />

        {/* Head */}
        <ellipse cx="60" cy="22" rx="16" ry="18" fill={bronzeMain} />

        {/* Hair */}
        <ellipse cx="60" cy="10" rx="14" ry="8" fill={bronzeDark} />
        <path d="M46 12 Q50 6 60 5 Q70 6 74 12" fill={bronzeDark} />
        <circle cx="48" cy="14" r="4" fill={bronzeDark} />
        <circle cx="72" cy="14" r="4" fill={bronzeDark} />
        <circle cx="60" cy="8" r="5" fill={bronzeDark} />
        <path d="M46 18 Q60 15 74 18" stroke={bronzeMain} strokeWidth="2" fill="none" />

        {/* Brow */}
        <path d="M48 20 L54 20" stroke={bronzeDark} strokeWidth="2.5" strokeLinecap="round" />
        <path d="M66 20 L72 20" stroke={bronzeDark} strokeWidth="2.5" strokeLinecap="round" />

        {/* Eyebrows */}
        <path
          d={isError ? "M49 19 L54 21" : isSuccess ? "M49 18 L54 17" : "M49 19 L54 19"}
          stroke={bronzeDark} strokeWidth="2" strokeLinecap="round"
          style={{ transition: 'all 0.3s ease' }}
        />
        <path
          d={isError ? "M66 21 L71 19" : isSuccess ? "M66 17 L71 18" : "M66 19 L71 19"}
          stroke={bronzeDark} strokeWidth="2" strokeLinecap="round"
          style={{ transition: 'all 0.3s ease' }}
        />

        {/* Eyes */}
        <g style={{ transition: 'opacity 0.2s ease' }} opacity={isTyping ? 0 : 1}>
          <ellipse cx="51" cy="24" rx="3.5" ry={isSuccess ? 1.5 : 2.5} fill="#FFF8DC" />
          <circle cx="51" cy="24" r={isSuccess ? 1 : 1.5} fill="#1F2937" />
          <ellipse cx="69" cy="24" rx="3.5" ry={isSuccess ? 1.5 : 2.5} fill="#FFF8DC" />
          <circle cx="69" cy="24" r={isSuccess ? 1 : 1.5} fill="#1F2937" />
        </g>

        {/* Closed eyes when typing */}
        {isTyping && (
          <g>
            <path d="M48 24 Q51 26 54 24" stroke="#1F2937" strokeWidth="2" fill="none" strokeLinecap="round" />
            <path d="M66 24 Q69 26 72 24" stroke="#1F2937" strokeWidth="2" fill="none" strokeLinecap="round" />
          </g>
        )}

        {/* Nose */}
        <path d="M60 24 L58 30 L62 30 Z" fill={bronzeDark} />

        {/* Beard */}
        <path
          d="M44 28 Q42 32 44 38 Q48 48 60 50 Q72 48 76 38 Q78 32 76 28 Q72 30 68 32 L60 33 L52 32 Q48 30 44 28"
          fill={bronzeDark}
        />
        <path d="M48 34 Q50 38 48 42" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />
        <path d="M56 35 Q58 40 56 46" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />
        <path d="M64 35 Q62 40 64 46" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />
        <path d="M72 34 Q70 38 72 42" stroke={bronzeMain} strokeWidth="1" fill="none" opacity="0.5" />

        {/* Mustache */}
        <path d="M52 30 Q56 32 60 31 Q64 32 68 30" stroke={bronzeDark} strokeWidth="2.5" fill="none" strokeLinecap="round" />

        {/* Mouth */}
        <path
          d={isError ? "M56 33 Q60 32 64 33" : isSuccess ? "M55 33 Q60 35 65 33" : "M56 33 Q60 34 64 33"}
          stroke="#8B4513" strokeWidth="1" fill="none"
          style={{ transition: 'all 0.3s ease' }}
        />

        {/* Left Arm */}
        <g>
          <path
            d={isTyping ? "M35 52 L30 40 L45 28" : "M35 52 L25 70 L28 88"}
            stroke={bronzeMain} strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" fill="none"
            style={{ transition: 'd 0.4s ease-in-out' }}
          />
          <ellipse
            cx={isTyping ? 45 : 28} cy={isTyping ? 28 : 88}
            rx="7" ry="7" fill={bronzeMain}
            style={{ transition: 'cx 0.4s ease-in-out, cy 0.4s ease-in-out' }}
          />
        </g>

        {/* Right Arm with Spear */}
        <g>
          <path
            d={isTyping ? "M85 52 L90 40 L75 28" : "M85 52 L98 38 L102 20"}
            stroke={bronzeMain} strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" fill="none"
            style={{ transition: 'd 0.4s ease-in-out' }}
          />
          <ellipse
            cx={isTyping ? 75 : 102} cy={isTyping ? 28 : 20}
            rx="7" ry="7" fill={bronzeMain}
            style={{ transition: 'cx 0.4s ease-in-out, cy 0.4s ease-in-out' }}
          />
          <g style={{ opacity: isTyping ? 0 : 1, transition: 'opacity 0.3s ease-in-out' }}>
            <rect x="100" y="2" width="3" height="22" rx="1" fill="#5C4033" />
            <path d="M101.5 -12 L95 2 L108 2 Z" fill="#78716C" />
            <path d="M101.5 -8 L101.5 0" stroke="#A8A29E" strokeWidth="1" />
          </g>
        </g>

        {/* Success sparkles */}
        {isSuccess && (
          <g className="animate-sparkle">
            <polygon points="15,30 17,34 21,34 18,37 19,41 15,38 11,41 12,37 9,34 13,34" fill="#FCD34D" />
            <polygon points="110,50 112,54 116,54 113,57 114,61 110,58 106,61 107,57 104,54 108,54" fill="#FCD34D" />
            <polygon points="60,0 61,5 65,5 62,8 63,12 60,10 57,12 58,8 55,5 59,5" fill="#FCD34D" />
          </g>
        )}

        {/* Error sweat drop */}
        {isError && (
          <g>
            <ellipse cx="80" cy="15" rx="3" ry="5" fill="#87CEEB" />
            <ellipse cx="80" cy="13" rx="1.5" ry="2" fill="#B0E0E6" />
          </g>
        )}
      </svg>
    </div>
  );
};

export default VulcanMascot;
