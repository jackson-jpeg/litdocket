'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import {
  Scale,
  FileText,
  Calendar,
  Bell,
  CheckCircle,
  ArrowRight,
  X,
  Upload,
  Clock,
  Sparkles,
} from 'lucide-react';

const ONBOARDING_KEY = 'litdocket_onboarding_completed';
const ONBOARDING_DISMISSED_KEY = 'litdocket_onboarding_dismissed';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
}

const steps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to LitDocket',
    description: 'AI-powered legal docketing that helps you manage deadlines with confidence. Let\'s get you set up in 2 minutes.',
    icon: <Scale className="w-12 h-12 text-blue-600" />,
  },
  {
    id: 'upload',
    title: 'Upload Your First Document',
    description: 'Drop a legal document and our AI will automatically extract key dates, parties, and deadlines.',
    icon: <Upload className="w-12 h-12 text-blue-600" />,
    action: {
      label: 'Upload Document',
      href: '/tools/document-analyzer',
    },
  },
  {
    id: 'review',
    title: 'Review Extracted Deadlines',
    description: 'AI suggests deadlines with confidence scores. You review and approve before they hit your docket.',
    icon: <Clock className="w-12 h-12 text-blue-600" />,
  },
  {
    id: 'notifications',
    title: 'Set Up Notifications',
    description: 'Configure alerts based on deadline priority. Never miss a fatal deadline again.',
    icon: <Bell className="w-12 h-12 text-blue-600" />,
    action: {
      label: 'Configure Alerts',
      href: '/settings/notifications',
    },
  },
];

interface OnboardingWizardProps {
  onComplete?: () => void;
  forceShow?: boolean;
}

export function OnboardingWizard({ onComplete, forceShow = false }: OnboardingWizardProps) {
  const router = useRouter();
  const [isVisible, setIsVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    // Check if onboarding was already completed or dismissed
    const completed = localStorage.getItem(ONBOARDING_KEY);
    const dismissed = localStorage.getItem(ONBOARDING_DISMISSED_KEY);

    if (forceShow || (!completed && !dismissed)) {
      // Small delay for smoother entrance after page load
      const timer = setTimeout(() => setIsVisible(true), 500);
      return () => clearTimeout(timer);
    }
  }, [forceShow]);

  const handleDismiss = () => {
    localStorage.setItem(ONBOARDING_DISMISSED_KEY, 'true');
    setIsVisible(false);
  };

  const handleComplete = () => {
    localStorage.setItem(ONBOARDING_KEY, 'true');
    setIsVisible(false);
    onComplete?.();
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleAction = (step: OnboardingStep) => {
    if (step.action?.href) {
      handleComplete();
      router.push(step.action.href);
    } else if (step.action?.onClick) {
      step.action.onClick();
    }
  };

  if (!isVisible) return null;

  const step = steps[currentStep];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden"
        >
          {/* Header with progress */}
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-medium text-slate-700">
                Getting Started ({currentStep + 1}/{steps.length})
              </span>
            </div>
            <button
              onClick={handleDismiss}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-slate-100">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>

          {/* Content */}
          <div className="p-8 text-center">
            <div className="mb-6 flex justify-center">
              <div className="p-4 bg-blue-50 rounded-2xl">
                {step.icon}
              </div>
            </div>

            <h2 className="text-2xl font-bold text-slate-900 mb-3">
              {step.title}
            </h2>

            <p className="text-slate-600 leading-relaxed mb-8 max-w-sm mx-auto">
              {step.description}
            </p>

            {/* Action buttons */}
            <div className="flex flex-col gap-3">
              {step.action && (
                <button
                  onClick={() => handleAction(step)}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {step.action.label}
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              <button
                onClick={handleNext}
                className={`w-full flex items-center justify-center gap-2 px-6 py-3 font-medium rounded-lg transition-colors ${
                  step.action
                    ? 'text-slate-600 hover:bg-slate-100'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {currentStep === steps.length - 1 ? (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    Get Started
                  </>
                ) : step.action ? (
                  'Skip for now'
                ) : (
                  <>
                    Continue
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Step indicators */}
          <div className="px-8 pb-6 flex justify-center gap-2">
            {steps.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  idx === currentStep
                    ? 'bg-blue-600'
                    : idx < currentStep
                    ? 'bg-blue-300'
                    : 'bg-slate-200'
                }`}
                aria-label={`Go to step ${idx + 1}`}
              />
            ))}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

/**
 * Hook to check if onboarding should be shown
 */
export function useOnboarding() {
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    const completed = localStorage.getItem(ONBOARDING_KEY);
    const dismissed = localStorage.getItem(ONBOARDING_DISMISSED_KEY);
    setShouldShow(!completed && !dismissed);
  }, []);

  const resetOnboarding = () => {
    localStorage.removeItem(ONBOARDING_KEY);
    localStorage.removeItem(ONBOARDING_DISMISSED_KEY);
    setShouldShow(true);
  };

  return { shouldShow, resetOnboarding };
}

export default OnboardingWizard;
