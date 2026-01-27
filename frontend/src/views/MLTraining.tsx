import { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  BarChart3,
  Brain,
  CheckCircle,
  Cpu,
  Database,
  FileSpreadsheet,
  Play,
  RefreshCw,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Upload,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiClient } from '@/api/client';

// Types
interface ModelInfo {
  name: string;
  version: string;
  created_at: string;
  metrics: {
    r2?: number;
    mae?: number;
    rmse?: number;
    mape?: number;
  };
  features: string[];
}

interface TrainingFile {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: string;
}

interface TrainingResult {
  success: boolean;
  message: string;
  models_trained: string[];
  metrics: Record<string, any>;
  training_time_seconds: number;
}

type TabType = 'upload' | 'models' | 'training';

export default function MLTraining() {
  const [activeTab, setActiveTab] = useState<TabType>('upload');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [trainingFiles, setTrainingFiles] = useState<TrainingFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [, setUploadProgress] = useState(0);
  const [trainingResult, setTrainingResult] = useState<TrainingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch models and training data on mount
  useEffect(() => {
    fetchModels();
    fetchTrainingData();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await apiClient.get('/ml/models');
      setModels(response.data.models || []);
    } catch (err) {
      console.error('Failed to fetch models:', err);
    }
  };

  const fetchTrainingData = async () => {
    try {
      const response = await apiClient.get('/ml/training-data');
      setTrainingFiles(response.data.files || []);
    } catch (err) {
      console.error('Failed to fetch training data:', err);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Please upload a CSV file');
      return;
    }

    setIsLoading(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/ml/upload?train_after_upload=false', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        },
      });

      setUploadProgress(100);

      // Refresh training data list
      await fetchTrainingData();

      // Show success
      setError(null);
      alert(`Successfully uploaded ${response.data.rows_processed || 'N/A'} rows of training data`);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to upload file. Please try again.';
      setError(errorMessage);
      console.error('Upload error:', err);
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleGenerateSample = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/ml/generate-sample', {
        num_campaigns: 100,
        days_per_campaign: 30,
      });

      await fetchTrainingData();
      alert(`Generated ${response.data.rows} rows of sample training data`);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to generate sample data';
      setError(errorMessage);
      console.error('Generate sample error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTrainModels = async (useSampleData: boolean = false) => {
    setIsTraining(true);
    setTrainingResult(null);
    setError(null);

    try {
      const url = useSampleData
        ? '/ml/train?use_sample_data=true&num_campaigns=100&days=30'
        : '/ml/train';

      const response = await apiClient.post(url);

      setTrainingResult(response.data);
      await fetchModels();
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        'Training failed. Please ensure you have uploaded training data.';
      setError(errorMessage);
      console.error('Training error:', err);
    } finally {
      setIsTraining(false);
    }
  };

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`Are you sure you want to delete the ${modelName} model?`)) {
      return;
    }

    try {
      await apiClient.delete(`/ml/models/${modelName}`);
      await fetchModels();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to delete model';
      setError(errorMessage);
      console.error('Delete error:', err);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getModelIcon = (name: string) => {
    if (name.includes('roas')) return <TrendingUp className="w-5 h-5" />;
    if (name.includes('conversion')) return <Target className="w-5 h-5" />;
    if (name.includes('budget')) return <BarChart3 className="w-5 h-5" />;
    return <Brain className="w-5 h-5" />;
  };

  const tabs = [
    { id: 'upload' as TabType, label: 'Upload Data', icon: Upload },
    { id: 'models' as TabType, label: 'Models', icon: Brain },
    { id: 'training' as TabType, label: 'Train', icon: Cpu },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">ML Training</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Upload training data and manage ML models
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium',
              models.length > 0
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
            )}
          >
            <Cpu className="w-4 h-4" />
            {models.length} Models Ready
          </span>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 dark:text-red-400">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition-colors',
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
              )}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Upload Tab */}
      {activeTab === 'upload' && (
        <div className="space-y-6">
          {/* Upload Area */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Upload Training Data
            </h2>

            <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".csv"
                className="hidden"
              />
              <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-400 mb-2">
                Drag and drop your CSV file here, or
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Uploading...' : 'Browse Files'}
              </button>
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-4">
                Supported: CSV files from Kaggle (Facebook Ads, Google Ads) or generic format
              </p>
            </div>

            {/* Required Columns */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Required CSV Columns:
              </h3>
              <div className="flex flex-wrap gap-2">
                {[
                  'spend',
                  'impressions',
                  'clicks',
                  'conversions',
                  'revenue',
                  'platform',
                  'date',
                ].map((col) => (
                  <span
                    key={col}
                    className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm text-gray-600 dark:text-gray-400"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Generate Sample Data */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Or Generate Sample Data
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Generate synthetic training data for testing the ML pipeline
            </p>
            <button
              onClick={handleGenerateSample}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              <Sparkles className="w-5 h-5" />
              Generate 100 Campaigns (30 days each)
            </button>
          </div>

          {/* Training Files List */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Training Data Files
              </h2>
              <button
                onClick={fetchTrainingData}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <RefreshCw className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {trainingFiles.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                No training data uploaded yet
              </p>
            ) : (
              <div className="space-y-2">
                {trainingFiles.map((file) => (
                  <div
                    key={file.path}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Database className="w-5 h-5 text-blue-500" />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{file.name}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {formatBytes(file.size_bytes)} • {formatDate(file.modified_at)}
                        </p>
                      </div>
                    </div>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          {models.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Brain className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No Models Trained
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Upload training data and train models to get started
              </p>
              <button
                onClick={() => setActiveTab('training')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Go to Training
              </button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {models.map((model) => (
                <div
                  key={model.name}
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                        {getModelIcon(model.name)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 dark:text-white">
                          {model.name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                        </h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">v{model.version}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteModel(model.name)}
                      className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-gray-400 hover:text-red-500"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Metrics */}
                  <div className="space-y-2 mb-4">
                    {model.metrics.r2 !== undefined && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500 dark:text-gray-400">R² Score</span>
                        <span
                          className={cn(
                            'font-medium',
                            model.metrics.r2 > 0.7
                              ? 'text-green-600'
                              : model.metrics.r2 > 0.5
                                ? 'text-yellow-600'
                                : 'text-red-600'
                          )}
                        >
                          {(model.metrics.r2 * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {model.metrics.mae !== undefined && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500 dark:text-gray-400">MAE</span>
                        <span className="font-medium text-gray-900 dark:text-white">
                          {model.metrics.mae.toFixed(3)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Features */}
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Features:</p>
                    <div className="flex flex-wrap gap-1">
                      {model.features.slice(0, 4).map((feature) => (
                        <span
                          key={feature}
                          className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-400"
                        >
                          {feature}
                        </span>
                      ))}
                      {model.features.length > 4 && (
                        <span className="px-1.5 py-0.5 text-xs text-gray-500">
                          +{model.features.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
                    Created: {formatDate(model.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Training Tab */}
      {activeTab === 'training' && (
        <div className="space-y-6">
          {/* Training Options */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Train Models
            </h2>

            <div className="grid gap-4 md:grid-cols-2">
              {/* Train from Uploaded Data */}
              <div className="p-4 border border-gray-200 dark:border-gray-600 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <Database className="w-6 h-6 text-blue-500" />
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    Train from Uploaded Data
                  </h3>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Use your uploaded CSV training data to train models
                </p>
                <button
                  onClick={() => handleTrainModels(false)}
                  disabled={isTraining || trainingFiles.length === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isTraining ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Training...
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      Start Training
                    </>
                  )}
                </button>
                {trainingFiles.length === 0 && (
                  <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2">
                    Upload training data first
                  </p>
                )}
              </div>

              {/* Train from Sample Data */}
              <div className="p-4 border border-gray-200 dark:border-gray-600 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <Sparkles className="w-6 h-6 text-purple-500" />
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    Train from Sample Data
                  </h3>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Generate synthetic data and train models for testing
                </p>
                <button
                  onClick={() => handleTrainModels(true)}
                  disabled={isTraining}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {isTraining ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Training...
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      Quick Train
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Training Result */}
          {trainingResult && (
            <div
              className={cn(
                'rounded-xl border p-6',
                trainingResult.success
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
              )}
            >
              <div className="flex items-center gap-3 mb-4">
                {trainingResult.success ? (
                  <CheckCircle className="w-6 h-6 text-green-500" />
                ) : (
                  <XCircle className="w-6 h-6 text-red-500" />
                )}
                <h3
                  className={cn(
                    'font-semibold',
                    trainingResult.success
                      ? 'text-green-700 dark:text-green-400'
                      : 'text-red-700 dark:text-red-400'
                  )}
                >
                  {trainingResult.message}
                </h3>
              </div>

              {trainingResult.success && (
                <>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    Training completed in {trainingResult.training_time_seconds}s
                  </p>

                  <div className="space-y-3">
                    {trainingResult.models_trained.map((modelName) => {
                      const metrics = trainingResult.metrics[modelName] || {};
                      return (
                        <div
                          key={modelName}
                          className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            {getModelIcon(modelName)}
                            <span className="font-medium text-gray-900 dark:text-white">
                              {modelName}
                            </span>
                          </div>
                          <span
                            className={cn(
                              'text-sm font-medium',
                              metrics.r2 > 0.7
                                ? 'text-green-600'
                                : metrics.r2 > 0.5
                                  ? 'text-yellow-600'
                                  : 'text-red-600'
                            )}
                          >
                            R² = {metrics.r2 ? (metrics.r2 * 100).toFixed(1) : 'N/A'}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Models Being Trained Info */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
              Models That Will Be Trained
            </h3>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex items-start gap-3">
                <TrendingUp className="w-5 h-5 text-blue-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">ROAS Predictor</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Predicts Return on Ad Spend from campaign features
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Target className="w-5 h-5 text-green-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">
                    Conversion Predictor
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Predicts conversions based on spend and engagement
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <BarChart3 className="w-5 h-5 text-purple-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">Budget Impact</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Predicts revenue changes from budget adjustments
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
