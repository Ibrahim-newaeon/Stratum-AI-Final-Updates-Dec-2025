import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function CheckoutCancel() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center max-w-md mx-auto px-4">
        <h1 className="text-2xl font-bold font-display text-foreground mb-3">
          No worries
        </h1>
        <p className="text-muted-foreground mb-8">
          Your checkout was cancelled. No charges were made. You can try again whenever you're ready.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={() => navigate('/checkout')}
            className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-primary/90 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Try again
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center px-6 py-3 border border-border text-foreground font-medium rounded-xl hover:bg-accent transition-colors"
          >
            Back to dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
