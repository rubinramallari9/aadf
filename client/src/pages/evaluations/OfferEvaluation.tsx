// src/pages/evaluations/OfferEvaluation.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { offerApi, evaluationApi } from '../../api/api';

interface EvaluationCriteria {
  id: number;
  name: string;
  description?: string;
  weight: number;
  max_score: number;
  category: string;
}

interface EvaluationForm {
  criteria_id: number;
  score: number;
  comment: string;
}

interface Suggestion {
  suggested_score: number;
  confidence: number;
  max_score: number;
  criteria_name: string;
  criteria_category: string;
}

const OfferEvaluation: React.FC = () => {
  const { offerId } = useParams<{ offerId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [offer, setOffer] = useState<any>(null);
  const [criteria, setCriteria] = useState<EvaluationCriteria[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationForm[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<{ [key: number]: Suggestion }>({});
  const [loadingSuggestions, setLoadingSuggestions] = useState<{ [key: number]: boolean }>({});

  useEffect(() => {
    fetchOfferAndCriteria();
  }, [offerId]);

  const fetchOfferAndCriteria = async () => {
    try {
      setLoading(true);
      const offerResponse = await offerApi.getById(Number(offerId));
      setOffer(offerResponse);

      // Fetch existing evaluations for this offer by current evaluator
      const existingEvaluations = await evaluationApi.getAll({ 
        offer_id: Number(offerId),
        evaluator_id: user?.id 
      });

      // Fetch criteria for the tender
      const criteriaResponse = await evaluationApi.getAllCriteria({ 
        tender_id: offerResponse.tender 
      });
      setCriteria(criteriaResponse);

      // Initialize evaluations form
      const initialEvaluations = criteriaResponse.map((criterion: EvaluationCriteria) => {
        const existing = existingEvaluations.find((e: any) => e.criteria === criterion.id);
        return {
          criteria_id: criterion.id,
          score: existing ? existing.score : 0,
          comment: existing ? existing.comment : '',
        };
      });
      setEvaluations(initialEvaluations);
    } catch (err: any) {
      console.error('Error fetching offer details:', err);
      setError(err.message || 'Failed to load offer details');
    } finally {
      setLoading(false);
    }
  };

  const handleScoreChange = (criteriaId: number, value: string) => {
    const numValue = parseInt(value);
    const criterion = criteria.find(c => c.id === criteriaId);
    if (criterion && numValue >= 0 && numValue <= criterion.max_score) {
      setEvaluations(prev => prev.map(eval => 
        eval.criteria_id === criteriaId ? { ...eval, score: numValue } : eval
      ));
    }
  };

  const handleCommentChange = (criteriaId: number, value: string) => {
    setEvaluations(prev => prev.map(eval => 
      eval.criteria_id === criteriaId ? { ...eval, comment: value } : eval
    ));
  };

  const getSuggestion = async (criteriaId: number) => {
    try {
      setLoadingSuggestions(prev => ({ ...prev, [criteriaId]: true }));
      const suggestion = await evaluationApi.getSuggestion(Number(offerId), criteriaId);
      setSuggestions(prev => ({ ...prev, [criteriaId]: suggestion }));
    } catch (err: any) {
      console.error('Error getting suggestion:', err);
    } finally {
      setLoadingSuggestions(prev => ({ ...prev, [criteriaId]: false }));
    }
  };

  const applySuggestion = (criteriaId: number) => {
    const suggestion = suggestions[criteriaId];
    if (suggestion) {
      handleScoreChange(criteriaId, suggestion.suggested_score.toString());
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      await evaluationApi.bulkEvaluate(evaluations.map(eval => ({
        offer_id: Number(offerId),
        criteria_id: eval.criteria_id,
        score: eval.score,
        comment: eval.comment || undefined,
      })));
      navigate('/evaluations');
    } catch (err: any) {
      console.error('Error saving evaluations:', err);
      setError(err.message || 'Failed to save evaluations');
    } finally {
      setSaving(false);
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

  if (error || !offer) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error || 'Offer not found'}</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Evaluate Offer</h1>
          <p className="mt-1 text-sm text-gray-600">
            Vendor: {offer.vendor_name} | Tender: {offer.tender_reference}
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {criteria.map((criterion) => {
            const evaluation = evaluations.find(e => e.criteria_id === criterion.id);
            const suggestion = suggestions[criterion.id];
            const loadingSuggestion = loadingSuggestions[criterion.id];

            return (
              <div key={criterion.id} className="bg-white shadow rounded-lg p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{criterion.name}</h3>
                    <p className="mt-1 text-sm text-gray-600">{criterion.description}</p>
                  </div>
                  <div className="text-right">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Weight: {criterion.weight}%
                    </span>
                  </div>
                </div>

                <div className="mt-4">
                  <label htmlFor={`score-${criterion.id}`} className="block text-sm font-medium text-gray-700">
                    Score (0-{criterion.max_score})
                  </label>
                  <div className="mt-1 flex items-center">
                    <input
                      type="number"
                      id={`score-${criterion.id}`}
                      min="0"
                      max={criterion.max_score}
                      value={evaluation?.score || 0}
                      onChange={(e) => handleScoreChange(criterion.id, e.target.value)}
                      className="block w-24 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                    <span className="ml-2 text-sm text-gray-500">/ {criterion.max_score}</span>
                    
                    {/* AI Suggestion Button */}
                    <button
                      type="button"
                      onClick={() => getSuggestion(criterion.id)}
                      disabled={loadingSuggestion}
                      className="ml-4 inline-flex items-center px-3 py-1 border border-blue-300 rounded-md shadow-sm text-sm font-medium text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      {loadingSuggestion ? (
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        <span className="material-icons mr-1 text-lg">psychology</span>
                      )}
                      {loadingSuggestion ? 'Getting suggestion...' : 'Get AI Suggestion'}
                    </button>
                  </div>

                  {/* Show AI Suggestion */}
                  {suggestion && (
                    <div className="mt-3 p-4 bg-blue-50 rounded-md">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="text-sm text-blue-800">
                            <span className="font-medium">AI Suggested Score:</span> {suggestion.suggested_score} / {suggestion.max_score}
                          </p>
                          <p className="text-sm text-blue-700">
                            Confidence: {suggestion.confidence}%
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => applySuggestion(criterion.id)}
                          className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                          Apply Suggestion
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-4">
                  <label htmlFor={`comment-${criterion.id}`} className="block text-sm font-medium text-gray-700">
                    Comment
                  </label>
                  <textarea
                    id={`comment-${criterion.id}`}
                    rows={3}
                    value={evaluation?.comment || ''}
                    onChange={(e) => handleCommentChange(criterion.id, e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    placeholder="Enter your evaluation comments..."
                  />
                </div>
              </div>
            );
          })}

          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={() => navigate('/evaluations')}
              className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              {saving ? 'Saving...' : 'Save Evaluation'}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default OfferEvaluation;