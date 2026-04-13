import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ArrowRight } from 'lucide-react';

export default function CheckoutSuccess() {
  const navigate = useNavigate();
  useEffect(() => {
    // Auto-redirect after 5 seconds
    const timer = setTimeout(() => navigate('/dashboard'), 5000);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="w-16 h-16 rounded-full bg-status-healthy/10 flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 className="w-8 h-8 text-status-healthy" />
        </div>
        <h1 className="text-2xl font-bold font-display text-foreground mb-3">
          You're all set!
        </h1>
        <p className="text-muted-foreground mb-8">
          Your subscription is active. Your 14-day free trial has started — explore everything Stratum AI has to offer.
        </p>
        <button
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-primary/90 transition-colors"
        >
          Go to Dashboard
          <ArrowRight className="w-4 h-4 ml-2" />
        </button>
        <p className="text-xs text-muted-foreground mt-4">
          Redirecting automatically in 5 seconds...
        </p>
      </div>
    </div>
  );
}
