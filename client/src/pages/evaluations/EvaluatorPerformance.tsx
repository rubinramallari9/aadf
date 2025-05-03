// client/src/pages/evaluators/EvaluatorPerformance.tsx
import React, { useState, useEffect } from 'react';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { evaluationApi } from '../../api/api';
// Fix Recharts imports
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';

// Type declaration for Recharts components to fix TypeScript errors
declare module 'recharts' {
  interface BarChartProps {
    className?: string;
  }
  interface PieChartProps {
    className?: string;
  }
  // Removed duplicate declaration of XAxisProps to avoid conflict with recharts type definitions
  // Removed duplicate declaration of YAxisProps to avoid conflict with recharts type definitions
  // Removed custom TooltipProps interface to avoid conflict with recharts type definitions
  // Removed custom LegendProps interface to avoid conflict with recharts type definitions
  // Removed custom BarProps interface to avoid conflict with recharts type definitions
  // Removed custom PieProps interface to avoid conflict with recharts type definitions
  // Removed custom CellProps interface to avoid conflict with recharts type definitions
}

interface EvaluatorMetric {
  evaluator_id: number;
  evaluator_name: string;
  total_evaluations: number;
  tenders_evaluated: number;
  offers_evaluated: number;
  avg_score: number;
  avg_time_per_evaluation: string | null;
  score_std_dev: number;
  recent_activity: number;
  avg_completion_rate: number;
}

interface ScoreDistribution {
  total_evaluations: number;
  avg_score: number;
  distribution: Array<{
    label: string;
    count: number;
  }>;
  category_distribution: Array<{
    criteria__category: string;
    avg_score: number;
    count: number;
  }>;
  top_scoring_criteria: Array<{
    criteria__name: string;
    criteria__category: string;
    avg_score: number;
  }>;
  bottom_scoring_criteria: Array<{
    criteria__name: string;
    criteria__category: string;
    avg_score: number;
  }>;
}

// Type for Pie chart label
interface PieLabelProps {
  criteria__category: string;
  count: number;
  [key: string]: any;
}

const EvaluatorPerformance: React.FC = () => {
  const { user } = useAuth();
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [scoreDistribution, setScoreDistribution] = useState<ScoreDistribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchPerformanceData(),
      fetchScoreDistribution()
    ]).finally(() => setLoading(false));
  }, []);

  const fetchPerformanceData = async () => {
    try {
      const response = await evaluationApi.getPerformance();
      setPerformanceData(response);
    } catch (err: any) {
      console.error('Error fetching performance data:', err);
      setError(err.message || 'Failed to load performance data');
    }
  };

  const fetchScoreDistribution = async () => {
    try {
      const response = await evaluationApi.getScoreDistribution();
      setScoreDistribution(response);
    } catch (err: any) {
      console.error('Error fetching score distribution:', err);
      setError(err.message || 'Failed to load score distribution');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      </Layout>
    );
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Evaluator Performance Dashboard</h1>
        
        {/* Admin/Staff Overview */}
        {(user?.role === 'admin' || user?.role === 'staff') && performanceData?.evaluator_metrics && (
          <>
            <div className="bg-white shadow rounded-lg mb-8">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Evaluator Comparison</h2>
              </div>
              <div className="p-6">
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={performanceData.evaluator_metrics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="evaluator_name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="total_evaluations" fill="#8884d8" name="Total Evaluations" />
                    <Bar dataKey="avg_score" fill="#82ca9d" name="Average Score" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg mb-8">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Evaluator Performance Metrics</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Evaluator
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Total Evaluations
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tenders
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Avg Score
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Score Std Dev
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Completion Rate
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Recent Activity
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {performanceData.evaluator_metrics.map((metric: EvaluatorMetric) => (
                      <tr key={metric.evaluator_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {metric.evaluator_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.total_evaluations}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.tenders_evaluated}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.avg_score.toFixed(1)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={metric.score_std_dev > 20 ? 'text-red-600' : 'text-green-600'}>
                            {metric.score_std_dev.toFixed(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.avg_completion_rate}%
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.recent_activity} (last 30 days)
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* Score Distribution */}
        {scoreDistribution && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">Score Distribution</h2>
                </div>
                <div className="p-6">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={scoreDistribution.distribution}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="count" fill="#8884d8" name="Count" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">Category Distribution</h2>
                </div>
                <div className="p-6">
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={scoreDistribution.category_distribution}
                        dataKey="count"
                        nameKey="criteria__category"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        label={(entry: PieLabelProps) => `${entry.criteria__category}: ${entry.count}`}
                      >
                        {scoreDistribution.category_distribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">Top Scoring Criteria</h2>
                </div>
                <div className="p-6">
                  <table className="min-w-full">
                    <thead>
                      <tr>
                        <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Criteria
                        </th>
                        <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Category
                        </th>
                        <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Avg Score
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {scoreDistribution.top_scoring_criteria.map((criteria, index) => (
                        <tr key={index} className="border-t border-gray-200">
                          <td className="py-3 text-sm text-gray-900">{criteria.criteria__name}</td>
                          <td className="py-3 text-sm text-gray-500">{criteria.criteria__category}</td>
                          <td className="py-3 text-sm text-gray-900 text-right text-green-600">
                            {criteria.avg_score.toFixed(1)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">Lowest Scoring Criteria</h2>
                </div>
                <div className="p-6">
                  <table className="min-w-full">
                    <thead>
                      <tr>
                        <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Criteria
                        </th>
                        <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Category
                        </th>
                        <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Avg Score
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {scoreDistribution.bottom_scoring_criteria.map((criteria, index) => (
                        <tr key={index} className="border-t border-gray-200">
                          <td className="py-3 text-sm text-gray-900">{criteria.criteria__name}</td>
                          <td className="py-3 text-sm text-gray-500">{criteria.criteria__category}</td>
                          <td className="py-3 text-sm text-gray-900 text-right text-red-600">
                            {criteria.avg_score.toFixed(1)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Score Analysis</h2>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Total Evaluations</div>
                    <div className="text-3xl font-bold text-gray-900">{scoreDistribution.total_evaluations}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Average Score</div>
                    <div className="text-3xl font-bold text-gray-900">{scoreDistribution.avg_score.toFixed(1)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-500">Score Range</div>
                    <div className="text-3xl font-bold text-gray-900">
                      0-100
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
};

export default EvaluatorPerformance;