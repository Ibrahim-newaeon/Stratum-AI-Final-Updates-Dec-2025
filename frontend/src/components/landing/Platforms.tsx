// Apple Glass Dark theme
const theme = {
  primary: '#0A84FF',
  primaryLight: 'rgba(10, 132, 255, 0.15)',
  bgBase: '#000000',
  bgCard: 'rgba(255, 255, 255, 0.03)',
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.08)',
};

export function Platforms() {
  const platforms = [
    {
      name: 'Meta',
      api: 'Custom Audiences API',
      icon: MetaIcon,
      iconColor: 'rgba(255, 255, 255, 0.7)',
    },
    {
      name: 'Google',
      api: 'Customer Match API',
      icon: GoogleIcon,
      iconColor: 'rgba(255, 255, 255, 0.7)',
    },
    {
      name: 'TikTok',
      api: 'DMP Custom Audience API',
      icon: TikTokIcon,
      iconColor: 'rgba(255, 255, 255, 0.7)',
    },
    {
      name: 'Snapchat',
      api: 'Audience Match SAM API',
      icon: SnapchatIcon,
      iconColor: 'rgba(255, 255, 255, 0.5)',
    },
  ];

  return (
    <section className="py-24" style={{ background: theme.bgBase, borderTop: `1px solid ${theme.border}`, borderBottom: `1px solid ${theme.border}` }}>
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header - Centered */}
        <div className="text-center mb-12">
          <div className="flex justify-center mb-6">
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
              style={{
                background: theme.primaryLight,
                border: '1px solid rgba(10, 132, 255, 0.3)',
              }}
            >
              <span className="text-sm font-medium" style={{ color: theme.primary }}>
                Platform Integrations
              </span>
            </div>
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 text-center">
            One source of truth. <span style={{ color: theme.primary }}>Every platform.</span>
          </h2>
          <p className="text-lg text-center" style={{ color: theme.textMuted }}>
            Unified Across Your Entire Ad Stack
          </p>
        </div>

        {/* Platform Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-5xl mx-auto">
          {platforms.map((platform) => (
            <div
              key={platform.name}
              className="group flex flex-col items-center justify-center p-8 rounded-2xl transition-all duration-300 hover:-translate-y-1"
              style={{
                background: theme.bgCard,
                backdropFilter: 'blur(40px)',
                WebkitBackdropFilter: 'blur(40px)',
                border: `1px solid ${theme.border}`,
              }}
            >
              {/* Icon Container */}
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${theme.border}`,
                }}
              >
                <platform.icon
                  className="w-10 h-10"
                  style={{ color: platform.iconColor }}
                />
              </div>

              {/* Platform Name */}
              <span
                className="text-base font-medium text-white mb-1 text-center"
              >
                {platform.name}
              </span>

              {/* API Description */}
              <span
                className="text-xs text-center leading-tight"
                style={{ color: theme.textMuted }}
              >
                {platform.api}
              </span>
            </div>
          ))}
        </div>

        {/* Stats Section */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-center">
          <div className="px-8 py-4" style={{ borderRight: `1px solid ${theme.border}` }}>
            <div className="text-3xl font-bold text-white">4B+</div>
            <div className="text-sm" style={{ color: theme.textMuted }}>Events Processed</div>
          </div>
          <div className="px-8 py-4" style={{ borderRight: `1px solid ${theme.border}` }}>
            <div className="text-3xl font-bold text-white">$2.1B</div>
            <div className="text-sm" style={{ color: theme.textMuted }}>Ad Spend Managed</div>
          </div>
          <div className="px-8 py-4">
            <div className="text-3xl font-bold text-white">99.9%</div>
            <div className="text-sm" style={{ color: theme.textMuted }}>Uptime SLA</div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Platform Icons - Monochrome style
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
