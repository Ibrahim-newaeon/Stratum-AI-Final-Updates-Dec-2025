export function Platforms() {
  const platforms = [
    { name: 'Meta', color: '#0866FF', icon: MetaIcon },
    { name: 'Google', color: '#4285F4', icon: GoogleIcon },
    { name: 'TikTok', color: '#00F2EA', icon: TikTokIcon },
    { name: 'Snapchat', color: '#FFFC00', icon: SnapchatIcon },
    { name: 'GA4', color: '#E37400', icon: GA4Icon },
    { name: 'HubSpot', color: '#FF7A59', icon: HubSpotIcon },
    { name: 'Zoho', color: '#E42527', icon: ZohoIcon },
  ];

  return (
    <section className="py-24 bg-surface-secondary border-y border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-12">
          <p className="text-meta text-text-muted uppercase tracking-wider mb-4">
            Unified Across Your Entire Ad Stack
          </p>
          <h2 className="text-h2 text-white">One source of truth. Every platform.</h2>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16">
          {platforms.map((platform) => (
            <div
              key={platform.name}
              className="motion-card group flex flex-col items-center gap-3 p-4"
            >
              <div
                className="w-16 h-16 rounded-xl flex items-center justify-center transition-all duration-base"
                style={{ backgroundColor: `${platform.color}15` }}
              >
                <platform.icon className="w-8 h-8" style={{ color: platform.color }} />
              </div>
              <span className="text-meta text-text-secondary group-hover:text-white transition-colors">
                {platform.name}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-16 flex items-center justify-center gap-8 text-center">
          <div className="px-8 py-4 border-r border-white/10">
            <div className="text-h2 text-white font-bold">4B+</div>
            <div className="text-meta text-text-muted">Events Processed</div>
          </div>
          <div className="px-8 py-4 border-r border-white/10">
            <div className="text-h2 text-white font-bold">$2.1B</div>
            <div className="text-meta text-text-muted">Ad Spend Managed</div>
          </div>
          <div className="px-8 py-4">
            <div className="text-h2 text-white font-bold">99.9%</div>
            <div className="text-meta text-text-muted">Uptime SLA</div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Platform Icons
function MetaIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.51 1.49-3.89 3.78-3.89 1.09 0 2.23.19 2.23.19v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 0 0 8.44-9.9c0-5.53-4.5-10.02-10-10.02Z" />
    </svg>
  );
}

function GoogleIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

function TikTokIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z" />
    </svg>
  );
}

function SnapchatIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12.17 2c3 0 5.42 1.96 5.77 5.05.04.39.06.77.06 1.15 0 .7-.1 1.37-.26 2a.5.5 0 0 0 .31.61c.5.17 1.03.35 1.5.62.26.15.4.4.4.67 0 .24-.1.45-.33.58-.9.5-1.87.64-2.22.68-.03.5-.17.98-.55 1.43-.4.47-1.12 1.01-2.33 1.59-.05.03-.1.08-.12.14l-.17.54c-.04.14-.02.22.03.3.04.07.1.1.15.12.51.12 1 .32 1.35.63.23.2.38.45.38.75 0 .46-.32.83-.76 1.06-.52.27-1.16.4-1.8.4-.5 0-.95-.08-1.27-.15-.4-.09-.9-.22-1.42-.22-.5 0-1.01.13-1.43.22-.32.07-.76.15-1.26.15-.64 0-1.28-.13-1.8-.4-.44-.23-.76-.6-.76-1.06 0-.3.15-.55.38-.75.35-.31.84-.51 1.35-.63.06-.02.11-.05.15-.12.05-.08.07-.16.03-.3l-.17-.54c-.02-.06-.07-.11-.12-.14-1.21-.58-1.93-1.12-2.33-1.59-.38-.45-.52-.92-.55-1.43-.35-.04-1.32-.18-2.22-.68a.7.7 0 0 1-.33-.58c0-.27.14-.52.4-.67.47-.27 1-.45 1.5-.62a.5.5 0 0 0 .31-.61 8.8 8.8 0 0 1-.26-2c0-.38.02-.76.06-1.15C6.58 3.96 9 2 12 2h.17z" />
    </svg>
  );
}

function GA4Icon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.84 2.998v17.99a3 3 0 0 1-3 3.01h-3.02V9.998a3 3 0 0 1 3-3h3.02v-4zm-9.01 21v-6.01a3 3 0 0 0-3-3H7.82v9.01h6.01zm-9.01 0V15a3 3 0 0 0-3-3H1.8v12.01h2.01a1 1 0 0 0 1.01-1.01z" />
    </svg>
  );
}

function HubSpotIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.164 7.93V5.084a2.198 2.198 0 0 0 1.267-1.984v-.066A2.198 2.198 0 0 0 17.233.836h-.066a2.198 2.198 0 0 0-2.198 2.198v.066c0 .864.501 1.61 1.227 1.967v2.862a5.052 5.052 0 0 0-2.331 1.108l-6.156-4.785a2.625 2.625 0 0 0 .073-.548 2.612 2.612 0 0 0-2.611-2.611 2.612 2.612 0 0 0-2.612 2.611 2.612 2.612 0 0 0 2.612 2.612c.511 0 .987-.149 1.388-.405l6.040 4.696a5.058 5.058 0 0 0-.478 2.158 5.058 5.058 0 0 0 .498 2.199l-1.803 1.803a2.197 2.197 0 0 0-.648-.097 2.198 2.198 0 0 0-2.198 2.198 2.198 2.198 0 0 0 2.198 2.198 2.198 2.198 0 0 0 2.198-2.198c0-.237-.037-.465-.106-.679l1.765-1.765a5.063 5.063 0 0 0 3.048 1.025 5.073 5.073 0 0 0 5.072-5.073 5.073 5.073 0 0 0-4.122-4.98zM17.2 15.8a2.534 2.534 0 0 1-2.535-2.535A2.534 2.534 0 0 1 17.2 10.73a2.534 2.534 0 0 1 2.535 2.535A2.534 2.534 0 0 1 17.2 15.8z" />
    </svg>
  );
}

function ZohoIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.63 9.14h5.55L4.09 14.4H0l2.63-5.26zm5.85 5.26L14.1 3.57l2.13 4.25-3.69 7.38-3.23-6.46-3.07 6.13 2.24-.47zm12.89-5.26l-2.64 5.26h4.09L24 9.14h-2.63zm-5.55 0L12 16.02l-2.13-4.25 1.22-2.44 1.08 2.16.85-1.7.85 1.7 1.08-2.16 1.22 2.44.77-1.53h2.15l.28-.57-3.23-6.46-3.33 6.65-1.23-2.46-1.23 2.46-3.33-6.65-3.23 6.46.28.57h2.15l.77 1.53 1.22-2.44 1.08 2.16.85-1.7z" />
    </svg>
  );
}
