import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  FileText,
  GraduationCap,
  Lightbulb,
  PlayCircle,
  Search,
  X,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useJoyride } from './JoyrideWrapper';

interface LearningHubProps {
  isOpen: boolean;
  onClose: () => void;
}

interface LearningResource {
  id: string;
  type: 'video' | 'article' | 'tip';
  title: string;
  description: string;
  duration?: string;
  completed?: boolean;
}

interface LearningCategory {
  id: string;
  title: string;
  icon: React.ReactNode;
  resources: LearningResource[];
}

export function LearningHub({ isOpen, onClose }: LearningHubProps) {
  const { t } = useTranslation();
  const { startTour } = useJoyride();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories: LearningCategory[] = [
    {
      id: 'getting-started',
      title: t('learningHub.categories.gettingStarted'),
      icon: <GraduationCap className="w-5 h-5" />,
      resources: [
        {
          id: 'gs-1',
          type: 'video',
          title: t('learningHub.resources.platformOverview'),
          description: t('learningHub.resources.platformOverviewDesc'),
          duration: '5 min',
        },
        {
          id: 'gs-2',
          type: 'article',
          title: t('learningHub.resources.firstCampaign'),
          description: t('learningHub.resources.firstCampaignDesc'),
          duration: '3 min read',
        },
        {
          id: 'gs-3',
          type: 'tip',
          title: t('learningHub.resources.dashboardTips'),
          description: t('learningHub.resources.dashboardTipsDesc'),
        },
      ],
    },
    {
      id: 'analytics',
      title: t('learningHub.categories.analytics'),
      icon: <Lightbulb className="w-5 h-5" />,
      resources: [
        {
          id: 'an-1',
          type: 'video',
          title: t('learningHub.resources.understandingKPIs'),
          description: t('learningHub.resources.understandingKPIsDesc'),
          duration: '8 min',
        },
        {
          id: 'an-2',
          type: 'article',
          title: t('learningHub.resources.roasGuide'),
          description: t('learningHub.resources.roasGuideDesc'),
          duration: '5 min read',
        },
      ],
    },
    {
      id: 'automation',
      title: t('learningHub.categories.automation'),
      icon: <Zap className="w-5 h-5" />,
      resources: [
        {
          id: 'au-1',
          type: 'video',
          title: t('learningHub.resources.rulesEngine'),
          description: t('learningHub.resources.rulesEngineDesc'),
          duration: '10 min',
        },
        {
          id: 'au-2',
          type: 'article',
          title: t('learningHub.resources.automationBestPractices'),
          description: t('learningHub.resources.automationBestPracticesDesc'),
          duration: '7 min read',
        },
      ],
    },
  ];

  const getResourceIcon = (type: LearningResource['type']) => {
    switch (type) {
      case 'video':
        return <PlayCircle className="w-4 h-4 text-primary" />;
      case 'article':
        return <FileText className="w-4 h-4 text-primary" />;
      case 'tip':
        return <Lightbulb className="w-4 h-4 text-amber-500" />;
    }
  };

  const filteredCategories = categories
    .map((category) => ({
      ...category,
      resources: category.resources.filter(
        (resource) =>
          resource.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          resource.description.toLowerCase().includes(searchQuery.toLowerCase())
      ),
    }))
    .filter((category) => category.resources.length > 0);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-background border-l shadow-xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-primary" />
          <h2 className="font-semibold">{t('learningHub.title')}</h2>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-muted transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t('learningHub.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-4 border-b bg-muted/30">
        <button
          onClick={() => {
            startTour();
            onClose();
          }}
          className="w-full flex items-center gap-3 p-3 rounded-lg bg-primary/10 hover:bg-primary/20 transition-colors text-left"
        >
          <div className="p-2 rounded-lg bg-primary/20">
            <PlayCircle className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="font-medium text-sm">{t('learningHub.restartTour')}</p>
            <p className="text-xs text-muted-foreground">{t('learningHub.restartTourDesc')}</p>
          </div>
          <ChevronRight className="w-4 h-4 ml-auto text-muted-foreground" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {selectedCategory ? (
          // Show resources for selected category
          <div>
            <button
              onClick={() => setSelectedCategory(null)}
              className="text-sm text-primary hover:underline mb-4 flex items-center gap-1"
            >
              ← {t('learningHub.backToCategories')}
            </button>
            {categories
              .find((c) => c.id === selectedCategory)
              ?.resources.map((resource) => <ResourceCard key={resource.id} resource={resource} />)}
          </div>
        ) : (
          // Show categories
          filteredCategories.map((category) => (
            <div key={category.id}>
              <button
                onClick={() => setSelectedCategory(category.id)}
                className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">{category.icon}</div>
                  <div className="text-left">
                    <p className="font-medium">{category.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {category.resources.length} {t('learningHub.resources.count')}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </button>

              {/* Preview first 2 resources */}
              <div className="ml-12 mt-2 space-y-2">
                {category.resources.slice(0, 2).map((resource) => (
                  <div
                    key={resource.id}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    {getResourceIcon(resource.type)}
                    <span className="truncate">{resource.title}</span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t bg-muted/30">
        <p className="text-xs text-muted-foreground text-center">
          {t('learningHub.needHelp')}{' '}
          <a href="#" className="text-primary hover:underline">
            {t('learningHub.contactSupport')}
          </a>
        </p>
      </div>
    </div>
  );
}

function ResourceCard({ resource }: { resource: LearningResource }) {
  const getIcon = () => {
    switch (resource.type) {
      case 'video':
        return <PlayCircle className="w-5 h-5" />;
      case 'article':
        return <FileText className="w-5 h-5" />;
      case 'tip':
        return <Lightbulb className="w-5 h-5" />;
    }
  };

  return (
    <div
      className={cn(
        'p-4 rounded-lg border bg-card hover:shadow-md transition-shadow cursor-pointer mb-3',
        resource.completed && 'border-green-500/30 bg-green-500/5'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'p-2 rounded-lg',
            resource.type === 'video' && 'bg-primary/10 text-primary',
            resource.type === 'article' && 'bg-blue-500/10 text-blue-500',
            resource.type === 'tip' && 'bg-amber-500/10 text-amber-500'
          )}
        >
          {getIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-sm truncate">{resource.title}</h4>
            {resource.completed && (
              <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{resource.description}</p>
          {resource.duration && (
            <span className="text-xs text-muted-foreground mt-2 inline-block">
              {resource.duration}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default LearningHub;
