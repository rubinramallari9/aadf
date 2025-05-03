// src/pages/evaluations/EvaluationSummary.tsx
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'awarded':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'evaluated':
        return 'bg-yellow-100 text-yellow-800';
      case 'submitted':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
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

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Offers</div>
            <div className="mt-1 text-3xl font-semibol