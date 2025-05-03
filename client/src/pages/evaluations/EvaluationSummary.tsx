// client/src/pages/evaluations/EvaluationSummary.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { evaluationApi } from '../../api/api';

interface OfferSummary {
  offer_id: number;
  vendor_name: string;
  price: number;
  technical_score: number;
  financial_score: number;
  total_score: number;
  status: string;
  evaluation_count: number;
  evaluation_progress: {
    completed: number;
    total: number;
    percentage: number;
  };
  avg_score: number;
  criteria_scores: Array<{
    criteria__name: string;
    criteria__category: string;
    avg_score: number;
  }>;
}

interface EvaluationProgress {
  evaluator_id: number;
  evaluator_name: string;
  completed: number;
  total: number;
  percentage: number;
}

interface ConsistencyAnalysis {
  offer_id: number;
  vendor_name: string;
  criteria_id: number;
  criteria_name: string;
  variance: number;
  scores: number[];
}

interface Summary {
  tender_id: number;
  tender_reference: string;
  tender_title: string;
  tender_status: string;
  total_offers: number;
  total_evaluations: number;
  evaluators: Array<{
    evaluator__username: string;
    count: number;
  }>;
  avg_score: number;
  max_score: number;
  min_score: number;
  avg_scores_by_criteria: Array<{
    criteria__name: string;
    criteria__category: string;
    avg: number;
  }>;
  evaluation_status: {
    completed: number;
    total: number;
    percentage: number;
    evaluator_progress: EvaluationProgress[];
  };
  offers_summary: OfferSummary[];
  consistency_analysis?: ConsistencyAnalysis[];
}

const EvaluationSummary: React.FC = () => {
  const { tenderId } = useParams<{ tenderId: string }>();
  const { user } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    fetchSummary();
  }, [tenderId]);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const response = await evaluationApi.getSummary(Number(tenderId));
      setSummary(response);
    } catch (err: any) {
      console.error('Error fetching evaluation summary:', err);
      setError(err.message || 'Failed to load evaluation summary');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'awarded': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'evaluated': return 'bg-yellow-100 text-yellow-800';
      case 'submitted': return 'bg-blue-100 text-blue-800';
      case 'draft': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getScoreColor = (score: number, maxScore: number = 100) => {
    const percentage = (score / maxScore) * 100;
    if (percentage >= 80) return 'text-green-600';
    if (percentage >= 60) return 'text-yellow-600';
    return 'text-red-600';
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

  if (error || !summary) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error || 'Summary not found'}</span>
        </div>
      </Layout>
    );
  }

  const filterOffersByCategory = (category: string) => {
    if (category === 'all') return summary.offers_summary;
    return summary.offers_summary.filter(offer => {
      return offer.criteria_scores.some(cs => cs.criteria__category === category);
    });
  };

  const categories = Array.from(new Set(
    summary.avg_scores_by_criteria.map(score => score.criteria__category)
  ));

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Evaluation Summary</h1>
            <p className="mt-1 text-sm text-gray-600">
              Tender: {summary.tender_reference} - {summary.tender_title}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(summary.tender_status)}`}>
              {summary.tender_status}
            </span>
            <Link
              to={`/reports/generate?tender_id=${summary.tender_id}`}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <span className="material-icons mr-2">description</span>
              Generate Report
            </Link>
          </div>
        </div>

        {/* Overview Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Offers</div>
            <div className="mt-1 text-3xl font-semibold text-gray-900">{summary.total_offers}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Evaluations</div>
            <div className="mt-1 text-3xl font-semibold text-gray-900">{summary.total_evaluations}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Average Score</div>
            <div className={`mt-1 text-3xl font-semibold ${getScoreColor(summary.avg_score)}`}>
              {summary.avg_score?.toFixed(1) || 'N/A'}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Min Score</div>
            <div className={`mt-1 text-3xl font-semibold ${getScoreColor(summary.min_score, summary.max_score)}`}>
              {summary.min_score?.toFixed(1) || 'N/A'}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Max Score</div>
            <div className={`mt-1 text-3xl font-semibold ${getScoreColor(summary.max_score)}`}>
              {summary.max_score?.toFixed(1) || 'N/A'}
            </div>
          </div>
        </div>

        {/* Evaluation Progress */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Evaluation Progress</h2>
          </div>
          <div className="p-6">
            <div className="mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Overall Progress</span>
                <span className="text-sm font-medium text-gray-700">
                  {summary.evaluation_status.completed} / {summary.evaluation_status.total}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-600 h-3 rounded-full" 
                  style={{ width: `${summary.evaluation_status.percentage}%` }}
                ></div>
              </div>
            </div>

            <h3 className="text-sm font-medium text-gray-700 mb-4">Evaluator Progress</h3>
            <div className="space-y-4">
              {summary.evaluation_status.evaluator_progress.map((progress) => (
                <div key={progress.evaluator_id}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-700">{progress.evaluator_name}</span>
                    <span className="text-sm text-gray-700">
                      {progress.completed} / {progress.total} ({progress.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        progress.percentage === 100 ? 'bg-green-600' : 
                        progress.percentage >= 50 ? 'bg-yellow-400' : 
                        'bg-blue-600'
                      }`}
                      style={{ width: `${progress.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Average Scores by Criteria */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Average Scores by Criteria</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Criteria
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Average Score
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {summary.avg_scores_by_criteria.map((score, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {score.criteria__name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        score.criteria__category === 'technical' ? 'bg-blue-100 text-blue-800' :
                        score.criteria__category === 'financial' ? 'bg-green-100 text-green-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {score.criteria__category}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={getScoreColor(score.avg)}>
                        {score.avg.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Offer Rankings */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-medium text-gray-900">Offer Rankings</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    selectedCategory === 'all' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  All
                </button>
                {categories.map(category => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`px-3 py-1 rounded-full text-sm font-medium ${
                      selectedCategory === category ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vendor
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Technical Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Financial Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Price
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filterOffersByCategory(selectedCategory).map((offer, index) => (
                  <tr 
                    key={offer.offer_id} 
                    className={offer.status === 'awarded' ? 'bg-green-50' : undefined}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {index + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      <Link to={`/offers/${offer.offer_id}`} className="text-blue-600 hover:text-blue-900">
                        {offer.vendor_name}
                        {offer.status === 'awarded' && (
                          <span className="ml-2 material-icons text-green-600 text-sm align-middle">
                            emoji_events
                          </span>
                        )}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={getScoreColor(offer.technical_score || 0)}>
                        {offer.technical_score?.toFixed(1) || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={getScoreColor(offer.financial_score || 0)}>
                        {offer.financial_score?.toFixed(1) || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className={`font-bold ${getScoreColor(offer.total_score || 0)}`}>
                        {offer.total_score?.toFixed(1) || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(offer.status)}`}>
                        {offer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {offer.price?.toLocaleString() || 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Consistency Analysis */}
        {summary.consistency_analysis && summary.consistency_analysis.length > 0 && (
          <div className="bg-white shadow rounded-lg mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Evaluation Consistency Analysis</h2>
              <p className="text-sm text-gray-500 mt-1">
                Identifies criteria where evaluators have significant score differences
              </p>
            </div>
            <div className="p-6">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Vendor
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Criteria
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Variance
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Scores
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {summary.consistency_analysis.slice(0, 5).map((analysis, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {analysis.vendor_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {analysis.criteria_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className="text-red-600 font-medium">
                          {analysis.variance.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {analysis.scores.map((score, idx) => (
                          <span 
                            key={idx} 
                            className={`inline-block px-2 py-0.5 m-0.5 rounded-full text-xs ${
                              Math.abs(score - analysis.scores.reduce((a, b) => a + b, 0) / analysis.scores.length) > 10 
                                ? 'bg-red-100 text-red-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {score}
                          </span>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Evaluator Participation */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Evaluator Participation</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {summary.evaluators.map((evaluator, index) => (
                <div key={index} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <span className="inline-flex items-center justify-center h-10 w-10 rounded-full bg-blue-100">
                        <span className="material-icons text-blue-600">person</span>
                      </span>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {evaluator.evaluator__username}
                      </div>
                      <div className="text-sm text-gray-500">
                        {evaluator.count} evaluations
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default EvaluationSummary;