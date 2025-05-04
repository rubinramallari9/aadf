// src/pages/evaluations/EvaluationDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { evaluationApi } from '../../api/api';

interface Evaluation {
  id: number;
  offer: number;
  evaluator: number;
  evaluator_username: string;
  criteria: number;
  criteria_name: string;
  criteria_category: string;
  score: number;
  comment?: string;
  created_at: string;
  updated_at: string;
}

const EvaluationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvaluation();
  }, [id]);

  const fetchEvaluation = async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await evaluationApi.getById(parseInt(id));
      setEvaluation(response);
    } catch (err: any) {
      console.error('Error fetching evaluation:', err);
      setError(err.message || 'Failed to load evaluation details');
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

  if (!evaluation) {
    return (
      <Layout>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Evaluation Not Found</h1>
          <p className="mt-2 text-gray-600">The evaluation you are looking for does not exist or has been removed.</p>
          <Link to="/evaluations" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
            Back to Evaluations
          </Link>
        </div>
      </Layout>
    );
  }

  // Check if user has permission to view this evaluation
  const hasPermission = user && (
    user.role === 'admin' || 
    user.role === 'staff' || 
    user.id === evaluation.evaluator
  );

  if (!hasPermission) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">warning</span>
            <strong className="font-bold">Access Denied</strong>
          </div>
          <span className="block sm:inline mt-1"> You do not have permission to view this evaluation.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Evaluation Details</h1>
          <Link
            to="/evaluations"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <span className="material-icons mr-2 text-sm">arrow_back</span>
            Back to Evaluations
          </Link>
        </div>

        <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Evaluation Information
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">
              Details about the evaluation for criteria: {evaluation.criteria_name}
            </p>
          </div>
          <div className="border-t border-gray-200">
            <dl>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Evaluator</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {evaluation.evaluator_username}
                </dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Criteria</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {evaluation.criteria_name}
                </dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Category</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    evaluation.criteria_category === 'technical' ? 'bg-blue-100 text-blue-800' :
                    evaluation.criteria_category === 'financial' ? 'bg-green-100 text-green-800' :
                    'bg-purple-100 text-purple-800'
                  }`}>
                    {evaluation.criteria_category}
                  </span>
                </dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Score</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <div className="font-bold text-lg">{evaluation.score}</div>
                </dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Date Evaluated</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {new Date(evaluation.created_at).toLocaleString()}
                </dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {new Date(evaluation.updated_at).toLocaleString()}
                </dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Comment</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {evaluation.comment || 'No comment provided'}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <div className="flex justify-between items-center">
          <Link
            to={`/offers/${evaluation.offer}`}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <span className="material-icons mr-2 text-sm">visibility</span>
            View Offer
          </Link>

          {/* Only show edit button if this is the user's own evaluation or user is admin */}
          {(user?.id === evaluation.evaluator || user?.role === 'admin') && (
            <Link
              to={`/offers/${evaluation.offer}/evaluate`}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <span className="material-icons mr-2 text-sm">edit</span>
              Update Evaluation
            </Link>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default EvaluationDetail;