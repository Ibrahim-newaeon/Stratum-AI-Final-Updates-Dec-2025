/**
 * Landing Page - Marketing website for Stratum AI
 * Content is fetched from the CMS API with multi-language support
 */

import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  Brain,
  CheckCircle,
  ChevronRight,
  Globe,
  LineChart,
  MessageSquare,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
  Loader2,
} from 'lucide-react'

// Icon mapping for dynamic features
const iconMap: Record<string, typeof Brain> = {
  Brain,
  Globe,
  Zap,
  Target,
  LineChart,
  Shield,
  BarChart3,
  MessageSquare,
  Sparkles,
  TrendingUp,
}

// Platform logos as inline SVGs
const PlatformLogos = {
  Meta: () => (
    <svg viewBox="0 0 36 36" className="w-8 h-8">
      <defs>
        <linearGradient id="metaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0668E1" />
          <stop offset="50%" stopColor="#0080FB" />
          <stop offset="100%" stopColor="#00C6FF" />
        </linearGradient>
      </defs>
      <path fill="url(#metaGradient)" d="M8.5 6C5.5 6 3 8.5 3 12c0 3.5 2.5 8 5.5 12 3 4 6 7 8.5 7s5.5-3 8.5-7c3-4 5.5-8.5 5.5-12 0-3.5-2.5-6-5.5-6-3 0-5.5 3-8.5 7-3-4-5.5-7-8.5-7zm0 3c2 0 4 2 6.5 5.5.5.7 1 1.4 1.5 2.1l.5.7.5-.7c.5-.7 1-1.4 1.5-2.1C21 11 23 9 25 9c1.5 0 3 1.5 3 3.5 0 2.5-2 6-4.5 9.5-2.5 3.5-5 6-6.5 6s-4-2.5-6.5-6c-2.5-3.5-4.5-7-4.5-9.5 0-2 1.5-3.5 3-3.5z"/>
    </svg>
  ),
  Google: () => (
    <svg viewBox="0 0 48 48" className="w-8 h-8">
      <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
      <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
      <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
      <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
    </svg>
  ),
  TikTok: () => (
    <svg viewBox="0 0 48 48" className="w-8 h-8">
      <path fill="#00f2ea" d="M38.377,13.338c-2.099-1.47-3.577-3.704-4.025-6.299C34.275,6.604,34.225,6.177,34.198,5.75h-7.186l-0.009,26.926c-0.108,3.104-2.662,5.587-5.796,5.587c-1.053,0-2.046-0.276-2.899-0.766c-1.578-0.906-2.644-2.565-2.739-4.487c-0.151-3.073,2.199-5.672,5.253-5.811c0.324-0.015,0.645,0.009,0.961,0.06V19.97c-0.325-0.039-0.654-0.069-0.99-0.069c-6.867,0-12.433,5.519-12.505,12.369c-0.043,4.053,1.874,7.672,4.913,10.034c1.874,1.455,4.216,2.323,6.779,2.323c6.853,0,12.434-5.569,12.505-12.414l-0.047-13.377c2.692,1.919,5.981,3.042,9.52,3.042V14.594c-0.653,0-1.29-0.063-1.91-0.181C39.635,14.16,39.002,13.776,38.377,13.338z"/>
      <path fill="#ff004f" d="M38.377,13.338c-2.099-1.47-3.577-3.704-4.025-6.299C34.275,6.604,34.225,6.177,34.198,5.75h-7.186l-0.009,26.926c-0.108,3.104-2.662,5.587-5.796,5.587c-1.053,0-2.046-0.276-2.899-0.766c-1.578-0.906-2.644-2.565-2.739-4.487c-0.151-3.073,2.199-5.672,5.253-5.811c0.324-0.015,0.645,0.009,0.961,0.06V19.97c-0.325-0.039-0.654-0.069-0.99-0.069c-6.867,0-12.433,5.519-12.505,12.369c-0.043,4.053,1.874,7.672,4.913,10.034c1.874,1.455,4.216,2.323,6.779,2.323c6.853,0,12.434-5.569,12.505-12.414l-0.047-13.377c2.692,1.919,5.981,3.042,9.52,3.042V14.594c-0.653,0-1.29-0.063-1.91-0.181C39.635,14.16,39.002,13.776,38.377,13.338z" opacity=".5"/>
    </svg>
  ),
  Snapchat: () => (
    <svg viewBox="0 0 48 48" className="w-8 h-8">
      <path fill="#FFFC00" d="M24,4C12.954,4,4,12.954,4,24s8.954,20,20,20s20-8.954,20-20S35.046,4,24,4z"/>
      <path fill="#000" d="M35.7,28.3c-3.1-0.5-4.5-3.8-4.6-4c-0.1-0.2-0.2-0.3-0.2-0.5c0-0.4,0.3-0.6,0.8-0.8c0.2-0.1,0.5-0.2,0.8-0.3c0.8-0.3,1.4-0.6,1.4-1.2c0-0.5-0.4-0.9-1-0.9c-0.2,0-0.4,0.1-0.6,0.2c-0.3,0.1-0.6,0.3-1,0.3c-0.3,0-0.5-0.1-0.6-0.2c0.1-0.8,0.2-1.8,0.3-2.8c0.1-2.9-0.5-7.1-6.9-7.1c-6.4,0-7,4.2-6.9,7.1c0,1,0.2,2,0.3,2.8c-0.1,0.1-0.3,0.2-0.6,0.2c-0.4,0-0.7-0.2-1-0.3c-0.2-0.1-0.4-0.2-0.6-0.2c-0.6,0-1,0.4-1,0.9c0,0.6,0.6,0.9,1.4,1.2c0.3,0.1,0.6,0.2,0.8,0.3c0.5,0.2,0.8,0.4,0.8,0.8c0,0.1-0.1,0.3-0.2,0.5c-0.1,0.2-1.5,3.5-4.6,4c-0.5,0.1-0.8,0.5-0.7,1c0.1,0.5,0.6,0.9,1.7,1c0.7,0.1,1.1,0.2,1.2,0.7c0,0.2,0.1,0.4,0.2,0.6c0.2,0.3,0.5,0.5,0.9,0.5c0.4,0,0.9-0.1,1.5-0.3c0.9-0.3,2-0.6,3.5-0.1c0.8,0.3,1.5,0.9,2.3,1.5c1.1,0.9,2.4,2,4.2,2c0.1,0,0.1,0,0.2,0c0.1,0,0.1,0,0.2,0c1.8,0,3.1-1.1,4.2-2c0.8-0.7,1.5-1.2,2.3-1.5c1.5-0.5,2.6-0.2,3.5,0.1c0.6,0.2,1.1,0.3,1.5,0.3c0.4,0,0.7-0.2,0.9-0.5c0.1-0.2,0.1-0.4,0.2-0.6c0.1-0.5,0.5-0.6,1.2-0.7c1.1-0.1,1.6-0.5,1.7-1C36.5,28.8,36.2,28.4,35.7,28.3z"/>
    </svg>
  ),
  LinkedIn: () => (
    <svg viewBox="0 0 48 48" className="w-8 h-8">
      <path fill="#0077B5" d="M42,37c0,2.762-2.238,5-5,5H11c-2.761,0-5-2.238-5-5V11c0-2.762,2.239-5,5-5h26c2.762,0,5,2.238,5,5V37z"/>
      <path fill="#fff" d="M12 19H17V36H12zM14.485 17h-.028C12.965 17 12 15.888 12 14.499 12 13.08 12.995 12 14.514 12c1.521 0 2.458 1.08 2.486 2.499C17 15.887 16.035 17 14.485 17zM36 36h-5v-9.099c0-2.198-1.225-3.698-3.192-3.698-1.501 0-2.313 1.012-2.707 1.99C24.957 25.543 25 26.511 25 27v9h-5V19h5v2.616C25.721 20.5 26.85 19 29.738 19c3.578 0 6.261 2.25 6.261 7.274L36 36 36 36z"/>
    </svg>
  ),
  X: () => (
    <svg viewBox="0 0 24 24" className="w-8 h-8">
      <path fill="#000" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>
  ),
  WhatsApp: () => (
    <svg viewBox="0 0 48 48" className="w-8 h-8">
      <path fill="#25D366" d="M24,4C12.954,4,4,12.954,4,24c0,3.807,1.078,7.363,2.942,10.397L4.104,43.6c-0.153,0.506,0.311,0.97,0.817,0.817l9.203-2.838C17.031,42.922,20.387,44,24,44c11.046,0,20-8.954,20-20S35.046,4,24,4z"/>
      <path fill="#fff" d="M34.6,29.7c-0.5-0.2-2.8-1.4-3.2-1.5c-0.4-0.2-0.7-0.2-1,0.2c-0.3,0.4-1.2,1.5-1.5,1.8c-0.3,0.3-0.5,0.4-1,0.1c-0.5-0.2-2-0.7-3.8-2.3c-1.4-1.2-2.4-2.8-2.6-3.2c-0.3-0.5,0-0.7,0.2-0.9c0.2-0.2,0.5-0.5,0.7-0.8c0.2-0.2,0.3-0.4,0.5-0.7c0.2-0.3,0.1-0.6,0-0.8c-0.1-0.2-1-2.4-1.4-3.3c-0.4-0.9-0.7-0.8-1-0.8c-0.3,0-0.6,0-0.9,0c-0.3,0-0.8,0.1-1.3,0.6c-0.4,0.5-1.6,1.6-1.6,3.8c0,2.2,1.6,4.4,1.9,4.7c0.2,0.3,3.2,5,7.8,7c1.1,0.5,1.9,0.8,2.6,1c1.1,0.3,2.1,0.3,2.8,0.2c0.9-0.1,2.8-1.1,3.2-2.2c0.4-1.1,0.4-2.1,0.3-2.3C35.3,30,35,29.9,34.6,29.7z"/>
    </svg>
  ),
}

const platforms = [
  { name: 'Meta', Logo: PlatformLogos.Meta },
  { name: 'Google', Logo: PlatformLogos.Google },
  { name: 'TikTok', Logo: PlatformLogos.TikTok },
  { name: 'Snapchat', Logo: PlatformLogos.Snapchat },
  { name: 'LinkedIn', Logo: PlatformLogos.LinkedIn },
  { name: 'X (Twitter)', Logo: PlatformLogos.X },
  { name: 'WhatsApp', Logo: PlatformLogos.WhatsApp },
]

// Default content (fallback)
const defaultContent = {
  hero: {
    badge: 'AI-Powered Marketing Intelligence',
    title_line1: 'Unify Your Ad Platforms.',
    title_line2: 'Amplify Your Results.',
    subtitle: 'Stratum AI consolidates Meta, Google, TikTok, Snapchat, and LinkedIn into one intelligent platform. Get AI-powered predictions, automated optimization, and real-time insights.',
    cta_primary: 'Start Free Trial',
    cta_secondary: 'See How It Works',
  },
  stats: {
    items: [
      { value: '50%', label: 'Time Saved on Reporting' },
      { value: '32%', label: 'Average ROAS Improvement' },
      { value: '5+', label: 'Platforms Unified' },
      { value: '24/7', label: 'Automated Monitoring' },
    ],
  },
  features: {
    items: [
      { icon: 'Brain', title: 'AI-Powered Intelligence', description: 'Machine learning models predict ROAS, optimize budgets, and identify growth opportunities automatically.' },
      { icon: 'Globe', title: 'Unified Multi-Platform', description: 'Connect Meta, Google, TikTok, Snapchat, and LinkedIn in one dashboard. No more platform switching.' },
      { icon: 'Zap', title: 'Smart Automation', description: 'IFTTT-style rules that pause underperformers, reallocate budgets, and send alerts automatically.' },
      { icon: 'Target', title: 'Competitor Intelligence', description: 'Track competitors, benchmark performance, and identify market opportunities in real-time.' },
      { icon: 'LineChart', title: 'Real-Time Analytics', description: 'Live dashboards with KPIs, trends, and custom reports. Make decisions with confidence.' },
      { icon: 'Shield', title: 'GDPR Compliant', description: 'Enterprise-grade security with PII encryption, audit trails, and data export capabilities.' },
    ],
  },
  pricing: {
    title: 'Simple, Transparent Pricing',
    subtitle: 'Start free, upgrade when you\'re ready. No hidden fees.',
    plans: [
      { name: 'Starter', price: '$49', period: 'per month', description: 'For small teams getting started', features: ['5 team members', '25 campaigns', '2 ad platforms', '10 automation rules', 'Basic AI predictions', '90-day data retention', 'Email support'], cta: 'Start 14-Day Free Trial', popular: false },
      { name: 'Professional', price: '$199', period: 'per month', description: 'For growing marketing teams', features: ['15 team members', '100 campaigns', '5 ad platforms', '50 automation rules', 'Advanced AI predictions', '20 competitor tracking', '1-year data retention', 'API access', 'Priority support'], cta: 'Start 14-Day Free Trial', popular: true },
      { name: 'Enterprise', price: 'Custom', period: 'contact us', description: 'For large organizations', features: ['Unlimited team members', 'Unlimited campaigns', 'All ad platforms', 'Unlimited automation', 'Full AI capabilities', 'Unlimited competitors', 'Unlimited data retention', 'White-label option', 'Dedicated success manager', 'SLA guarantee'], cta: 'Contact Sales', popular: false },
    ],
  },
  testimonials: {
    title: 'Trusted by Marketing Teams Worldwide',
    subtitle: 'See what our customers have to say about Stratum AI.',
    items: [
      { quote: 'Stratum AI transformed how we manage ads. We cut reporting time by 60% and improved ROAS by 40%.', author: 'Sarah Chen', role: 'Head of Performance Marketing', company: 'TechScale Inc.' },
      { quote: 'The AI predictions are incredibly accurate. It\'s like having a data scientist on the team 24/7.', author: 'Michael Torres', role: 'Digital Marketing Director', company: 'GrowthBox' },
      { quote: 'Finally, one platform for all our ad channels. The automation rules alone saved us 20 hours per week.', author: 'Emma Williams', role: 'CMO', company: 'Velocity Commerce' },
    ],
  },
  cta: {
    title: 'Ready to Transform Your Marketing?',
    subtitle: 'Join thousands of marketing teams using Stratum AI to maximize their advertising ROI.',
    button: 'Start Your Free Trial',
    note: 'No credit card required. 14-day free trial.',
  },
}

// Types
interface CMSContent {
  hero?: typeof defaultContent.hero
  stats?: typeof defaultContent.stats
  features?: typeof defaultContent.features
  pricing?: typeof defaultContent.pricing
  testimonials?: typeof defaultContent.testimonials
  cta?: typeof defaultContent.cta
}

export default function Landing() {
  const [searchParams] = useSearchParams()
  const [content, setContent] = useState<CMSContent>(defaultContent)
  const [isLoading, setIsLoading] = useState(true)
  const [language, setLanguage] = useState('en')

  // Detect language from URL or browser
  useEffect(() => {
    const urlLang = searchParams.get('lang')
    if (urlLang && ['en', 'ar'].includes(urlLang)) {
      setLanguage(urlLang)
    } else {
      // Check browser language
      const browserLang = navigator.language.split('-')[0]
      if (browserLang === 'ar') {
        setLanguage('ar')
      }
    }
  }, [searchParams])

  // Fetch content from CMS
  useEffect(() => {
    const fetchContent = async () => {
      try {
        const res = await fetch(`/api/v1/landing-cms/public/all?language=${language}`)
        if (res.ok) {
          const data = await res.json()
          if (data.sections && Object.keys(data.sections).length > 0) {
            setContent({
              hero: data.sections.hero || defaultContent.hero,
              stats: data.sections.stats || defaultContent.stats,
              features: data.sections.features || defaultContent.features,
              pricing: data.sections.pricing || defaultContent.pricing,
              testimonials: data.sections.testimonials || defaultContent.testimonials,
              cta: data.sections.cta || defaultContent.cta,
            })
          }
        }
      } catch (err) {
        console.error('Failed to fetch CMS content:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchContent()
  }, [language])

  // Set document direction for RTL
  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = language
  }, [language])

  const hero = content.hero || defaultContent.hero
  const stats = content.stats || defaultContent.stats
  const features = content.features || defaultContent.features
  const pricing = content.pricing || defaultContent.pricing
  const testimonials = content.testimonials || defaultContent.testimonials
  const cta = content.cta || defaultContent.cta

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-lg border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="h-9 w-9 rounded-lg bg-gradient-stratum flex items-center justify-center shadow-glow">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span className="text-xl font-bold bg-gradient-stratum bg-clip-text text-transparent">
                Stratum AI
              </span>
            </div>

            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                {language === 'ar' ? 'المميزات' : 'Features'}
              </a>
              <a href="#platforms" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                {language === 'ar' ? 'المنصات' : 'Platforms'}
              </a>
              <a href="#pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                {language === 'ar' ? 'الأسعار' : 'Pricing'}
              </a>
              <a href="#testimonials" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                {language === 'ar' ? 'آراء العملاء' : 'Testimonials'}
              </a>
            </div>

            <div className="flex items-center gap-3">
              {/* Language Switcher */}
              <button
                onClick={() => setLanguage(language === 'en' ? 'ar' : 'en')}
                className="px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors border rounded-lg"
              >
                {language === 'en' ? 'عربي' : 'EN'}
              </button>
              <Link
                to="/login"
                className="px-4 py-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                {language === 'ar' ? 'تسجيل الدخول' : 'Login'}
              </Link>
              <Link
                to="/signup"
                className="px-4 py-2 text-sm font-medium text-white bg-gradient-stratum rounded-lg shadow-glow hover:shadow-glow-lg transition-all"
              >
                {language === 'ar' ? 'ابدأ مجاناً' : 'Start Free'}
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />

        <div className="max-w-7xl mx-auto relative">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              <span>{hero.badge}</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
              {hero.title_line1}
              <br />
              <span className="bg-gradient-stratum bg-clip-text text-transparent">
                {hero.title_line2}
              </span>
            </h1>

            <p className="text-lg sm:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              {hero.subtitle}
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
              <Link
                to="/signup"
                className="w-full sm:w-auto px-8 py-4 text-lg font-semibold text-white bg-gradient-stratum rounded-xl shadow-glow hover:shadow-glow-lg hover:scale-105 transition-all flex items-center justify-center gap-2"
              >
                {hero.cta_primary}
                <ArrowRight className="w-5 h-5" />
              </Link>
              <a
                href="#features"
                className="w-full sm:w-auto px-8 py-4 text-lg font-semibold text-foreground bg-muted rounded-xl hover:bg-muted/80 transition-colors flex items-center justify-center gap-2"
              >
                {hero.cta_secondary}
                <ChevronRight className="w-5 h-5" />
              </a>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
              {stats.items?.map((stat: { value: string; label: string }) => (
                <div key={stat.label} className="text-center">
                  <div className="text-3xl sm:text-4xl font-bold bg-gradient-stratum bg-clip-text text-transparent">
                    {stat.value}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Platforms Section */}
      <section id="platforms" className="py-20 px-4 sm:px-6 lg:px-8 bg-muted/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              {language === 'ar' ? 'جميع منصات إعلاناتك في لوحة تحكم واحدة' : 'All Your Ad Platforms, One Dashboard'}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {language === 'ar'
                ? 'توقف عن التنقل بين المنصات. Stratum AI يوحد بياناتك من جميع قنوات الإعلان الرئيسية.'
                : 'Stop switching between platforms. Stratum AI unifies your data from all major advertising channels.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6">
            {platforms.map((platform) => (
              <div
                key={platform.name}
                className="flex items-center gap-3 px-6 py-4 bg-background rounded-xl border shadow-sm hover:shadow-md hover:scale-105 transition-all cursor-pointer group"
              >
                <div className="w-12 h-12 rounded-lg bg-muted/50 flex items-center justify-center group-hover:bg-muted transition-colors">
                  <platform.Logo />
                </div>
                <span className="font-semibold text-lg">{platform.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              {language === 'ar' ? 'كل ما تحتاجه للسيطرة على الإعلانات الرقمية' : 'Everything You Need to Dominate Digital Advertising'}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {language === 'ar'
                ? 'من التنبؤات بالذكاء الاصطناعي إلى التحسين الآلي، يمنحك Stratum AI الأدوات لتعظيم العائد على الإنفاق الإعلاني.'
                : 'From AI predictions to automated optimization, Stratum AI gives you the tools to maximize ROAS.'}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.items?.map((feature: { icon: string; title: string; description: string }) => {
              const Icon = iconMap[feature.icon] || Brain
              return (
                <div
                  key={feature.title}
                  className="p-6 bg-background rounded-2xl border hover:border-primary/50 hover:shadow-lg transition-all group"
                >
                  <div className="w-12 h-12 rounded-xl bg-gradient-stratum flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-muted/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              {language === 'ar' ? 'ابدأ في دقائق' : 'Get Started in Minutes'}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {language === 'ar' ? 'ثلاث خطوات بسيطة لتحويل أداء تسويقك.' : 'Three simple steps to transform your marketing performance.'}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '1',
                title: language === 'ar' ? 'اربط منصاتك' : 'Connect Your Platforms',
                description: language === 'ar' ? 'اربط حساباتك في Meta وGoogle وTikTok وSnapchat وLinkedIn في ثوانٍ.' : 'Link your Meta, Google, TikTok, Snapchat, and LinkedIn accounts in seconds.',
                icon: Globe,
              },
              {
                step: '2',
                title: language === 'ar' ? 'دع الذكاء الاصطناعي يحلل' : 'Let AI Analyze',
                description: language === 'ar' ? 'نماذج التعلم الآلي لدينا تعالج بياناتك للعثور على فرص التحسين.' : 'Our ML models process your data to find optimization opportunities.',
                icon: Brain,
              },
              {
                step: '3',
                title: language === 'ar' ? 'شاهد نتائجك تنمو' : 'Watch Results Grow',
                description: language === 'ar' ? 'القواعد الآلية وتوصيات الذكاء الاصطناعي تعزز عائدك باستمرار.' : 'Automated rules and AI recommendations boost your ROAS continuously.',
                icon: TrendingUp,
              },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-stratum flex items-center justify-center mx-auto mb-4 shadow-glow">
                  <span className="text-white font-bold text-2xl">{item.step}</span>
                </div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              {pricing.title || (language === 'ar' ? 'أسعار بسيطة وشفافة' : 'Simple, Transparent Pricing')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {pricing.subtitle || (language === 'ar' ? 'ابدأ مجاناً، وقم بالترقية عندما تكون جاهزاً. لا رسوم مخفية.' : 'Start free, upgrade when you\'re ready. No hidden fees.')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {pricing.plans?.map((plan: { name: string; price: string; period: string; description: string; features: string[]; cta: string; popular: boolean }) => (
              <div
                key={plan.name}
                className={`relative p-8 bg-background rounded-2xl border-2 ${
                  plan.popular ? 'border-primary shadow-glow' : 'border-border'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-stratum text-white text-sm font-medium rounded-full">
                    {language === 'ar' ? 'الأكثر شعبية' : 'Most Popular'}
                  </div>
                )}

                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground">/{plan.period}</span>
                </div>
                <p className="text-muted-foreground mb-6">{plan.description}</p>

                <ul className="space-y-3 mb-8">
                  {plan.features?.map((feature: string) => (
                    <li key={feature} className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  to="/signup"
                  className={`block w-full py-3 text-center font-semibold rounded-lg transition-all ${
                    plan.popular
                      ? 'bg-gradient-stratum text-white shadow-glow hover:shadow-glow-lg'
                      : 'bg-muted hover:bg-muted/80'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-20 px-4 sm:px-6 lg:px-8 bg-muted/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              {testimonials.title || (language === 'ar' ? 'موثوق من فرق التسويق حول العالم' : 'Trusted by Marketing Teams Worldwide')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {testimonials.subtitle || (language === 'ar' ? 'شاهد ماذا يقول عملاؤنا عن Stratum AI.' : 'See what our customers have to say about Stratum AI.')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.items?.map((testimonial: { quote: string; author: string; role: string; company: string }, index: number) => (
              <div
                key={index}
                className="p-6 bg-background rounded-2xl border"
              >
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <svg key={i} className="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 20 20">
                      <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                    </svg>
                  ))}
                </div>
                <p className="text-foreground mb-4 italic">"{testimonial.quote}"</p>
                <div>
                  <div className="font-semibold">{testimonial.author}</div>
                  <div className="text-sm text-muted-foreground">
                    {testimonial.role}, {testimonial.company}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-stratum p-12 text-center text-white">
            <div className="absolute -top-20 -right-20 w-80 h-80 bg-white/10 rounded-full blur-3xl" />
            <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-white/10 rounded-full blur-3xl" />

            <div className="relative">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                {cta.title}
              </h2>
              <p className="text-lg text-white/80 mb-8 max-w-xl mx-auto">
                {cta.subtitle}
              </p>
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-primary font-semibold rounded-xl hover:bg-white/90 transition-colors"
              >
                {cta.button}
                <ArrowRight className="w-5 h-5" />
              </Link>
              <p className="text-sm text-white/60 mt-4">
                {cta.note}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="h-9 w-9 rounded-lg bg-gradient-stratum flex items-center justify-center">
                  <span className="text-white font-bold text-lg">S</span>
                </div>
                <span className="text-xl font-bold">Stratum AI</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {language === 'ar'
                  ? 'منصة ذكاء التسويق الموحدة للفرق الحديثة.'
                  : 'The unified marketing intelligence platform for modern teams.'}
              </p>
            </div>

            <div>
              <h4 className="font-semibold mb-4">{language === 'ar' ? 'المنتج' : 'Product'}</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-foreground transition-colors">{language === 'ar' ? 'المميزات' : 'Features'}</a></li>
                <li><a href="#pricing" className="hover:text-foreground transition-colors">{language === 'ar' ? 'الأسعار' : 'Pricing'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'التكاملات' : 'Integrations'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">API</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">{language === 'ar' ? 'الشركة' : 'Company'}</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'عن الشركة' : 'About'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'المدونة' : 'Blog'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'الوظائف' : 'Careers'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'اتصل بنا' : 'Contact'}</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4">{language === 'ar' ? 'القانوني' : 'Legal'}</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'سياسة الخصوصية' : 'Privacy Policy'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'شروط الخدمة' : 'Terms of Service'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">{language === 'ar' ? 'سياسة الكوكيز' : 'Cookie Policy'}</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">GDPR</a></li>
              </ul>
            </div>
          </div>

          <div className="pt-8 border-t text-center text-sm text-muted-foreground">
            <p>&copy; {new Date().getFullYear()} Stratum AI. {language === 'ar' ? 'جميع الحقوق محفوظة.' : 'All rights reserved.'}</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
