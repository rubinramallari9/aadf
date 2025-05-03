// client/src/components/evaluations/TransparentEvaluationForm.tsx
import React, { useState, useEffect } from 'react';
import { evaluationApi, offerApi } from '../../api/api';

interface EvaluationCriteria {
  id: number;
  name: string;
  description?: string;
  weight: number;
  max_score: number;
  category: string;
}

interface EvaluationFormData {
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

interface TransparentEvaluationFormProps {
  offer: any;
  criteria: EvaluationCriteria[];
  initialEvaluations: EvaluationFormData[];
  onSave: (evaluations: EvaluationFormData[]) => Promise<void>;
}

const TransparentEvaluationForm: React.FC<TransparentEvaluationFormProps> = ({
  offer,
  criteria,
  initialEvaluations,
  onSave
}) => {
  const [evaluations, setEvaluations] = useState<EvaluationFormData[]>(initialEvaluations);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<{ [key: number]: Suggestion }>({});
  const [loadingSuggestions, setLoadingSuggestions] = useState<{ [key: number]: boolean }>({});
  const [expandedComments, setExpandedComments] = useState<{ [key: number]: boolean }>({});

  // Group criteria by category for better organization
  const groupedCriteria = criteria.reduce((acc, criterion) => {
    if (!acc[criterion.category]) {
      acc[criterion.category] = [];
    }
    acc[criterion.category].push(criterion);
    return acc;
  }, {} as { [key: string]: EvaluationCriteria[] });

  const handleScoreChange = (criteriaId: number, value: string) => {
    const numValue = parseInt(value);
    const criterion = criteria.find(c => c.id === criteriaId);
    if (criterion && numValue >= 0 && numValue <= criterion.max_score) {
      setEvaluations(prev => prev.map(evaluation => 
        evaluation.criteria_id === criteriaId ? { ...evaluation, score: numValue } : evaluation
      ));
    }
  };

  const handleCommentChange = (criteriaId: number, value: string) => {
    setEvaluations(prev => prev.map(evaluation => 
      evaluation.criteria_id === criteriaId ? { ...evaluation, comment: value } : evaluation
    ));
  };

  const getSuggestion = async (criteriaId: number) => {
    try {
      setLoadingSuggestions(prev => ({ ...prev, [criteriaId]: true }));
      const suggestion = await evaluationApi.getSuggestion(offer.id, criteriaId);
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

  const calculateCategoryScore = (category: string, categoryCriteria: EvaluationCriteria[]) => {
    const categoryEvaluations = evaluations.filter(evaluation => 
      categoryCriteria.some(c => c.id === evaluation.criteria_id)
    );
    
    let weightedScore = 0;
    let totalWeight = 0;
    
    categoryCriteria.forEach(criterion => {
      const evaluation = categoryEvaluations.find(e => e.criteria_id === criterion.id);
      if (evaluation) {
        weightedScore += (evaluation.score / criterion.max_score) * criterion.weight;
        totalWeight += criterion.weight;
      }
    });
    
    return totalWeight > 0 ? (weightedScore / totalWeight) * 100 : 0;
  };

  const calculateOverallScore = () => {
    const categoryScores = Object.entries(groupedCriteria).map(([category, categoryCriteria]) => ({
      category,
      score: calculateCategoryScore(category, categoryCriteria),
      weight: categoryCriteria.reduce((sum, criterion) => sum + criterion.weight, 0),
    }));

    // Apply overall weights (Technical: 70%, Financial: 30%)
    const technicalScore = categoryScores.find(cs => cs.category === 'technical')?.score || 0;
    const financialScore = categoryScores.find(cs => cs.category === 'financial')?.score || 0;
    
    return (technicalScore * 0.7) + (financialScore * 0.3);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate all criteria have been scored
    const hasEmptyScores = evaluations.some(evaluation => evaluation.score === 0);
    if (hasEmptyScores) {
      setError('Please score all evaluation criteria before submitting');
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      await onSave(evaluations);
    } catch (err: any) {
      console.error('Error saving evaluations:', err);
      setError(err.message || 'Failed to save evaluations');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Evaluation Header */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Evaluation Form - {offer.vendor_name}
              </h3>
              <div className="mt-2 max-w-xl text-sm text-gray-500">
                <p>Tender: {offer.tender_reference}</p>
                <p>Technical weight: 70% | Financial weight: 30%</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-gray-900">
                {calculateOverallScore().toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">Overall Score</div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* Evaluation Criteria by Category */}
      {Object.entries(groupedCriteria).map(([category, categoryCriteria]) => (
        <div key={category} className="space-y-4">
          <div className="bg-gray-100 px-4 py-2 rounded-lg">
            <h2 className="text-xl font-bold text-gray-900 capitalize">
              {category} Criteria
            </h2>
            <div className="text-sm text-gray-600">
              Category Score: {calculateCategoryScore(category, categoryCriteria).toFixed(1)}%
            </div>
          </div>
          
          {categoryCriteria.map((criterion) => {
            const evaluation = evaluations.find(e => e.criteria_id === criterion.id);
            const suggestion = suggestions[criterion.id];
            const loadingSuggestion = loadingSuggestions[criterion.id];
            const isExpanded = expandedComments[criterion.id];

            return (
              <div key={criterion.id} className="bg-white shadow sm:rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex-grow mr-4">
                      <h3 className="text-lg font-medium text-gray-900">{criterion.name}</h3>
                      {criterion.description && (
                        <p className="mt-1 text-sm text-gray-600">{criterion.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                        Weight: {criterion.weight}%
                      </span>
                      <span className="inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                        Max: {criterion.max_score}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label htmlFor={`score-${criterion.id}`} className="block text-sm font-medium text-gray-700">
                      Score
                    </label>
                    <div className="mt-1 flex items-center gap-4">
                      <input
                        type="number"
                        id={`score-${criterion.id}`}
                        min="0"
                        max={criterion.max_score}
                        value={evaluation?.score || 0}
                        onChange={(e) => handleScoreChange(criterion.id, e.target.value)}
                        className="block w-24 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      />
                      <span className="text-sm text-gray-500">/ {criterion.max_score}</span>
                      
                      {/* AI Suggestion Button */}
                      <button
                        type="button"
                        onClick={() => getSuggestion(criterion.id)}
                        disabled={loadingSuggestion}
                        className="inline-flex items-center px-3 py-1 border border-blue-300 rounded-md shadow-sm text-sm font-medium text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                      >
                        {loadingSuggestion ? (
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        ) : (
                          <span className="material-icons mr-1 text-lg">psychology</span>
                        )}
                        {loadingSuggestion ? 'Getting AI suggestion...' : 'Get AI Suggestion'}
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
                      Comments
                    </label>
                    <textarea
                      id={`comment-${criterion.id}`}
                      rows={isExpanded ? 5 : 3}
                      value={evaluation?.comment || ''}
                      onChange={(e) => handleCommentChange(criterion.id, e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      placeholder={`Enter your evaluation comments for ${criterion.name.toLowerCase()}...`}
                    />
                    <button
                      type="button"
                      onClick={() => setExpandedComments(prev => ({ ...prev, [criterion.id]: !isExpanded }))}
                      className="mt-1 text-sm text-blue-600 hover:text-blue-800"
                    >
                      {isExpanded ? 'Collapse' : 'Expand'} comment field
                    </button>
                  </div>

                  {/* Score Progress Bar */}
                  <div className="mt-4">
                    <div className="flex justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">Score Progress</span>
                      <span className="text-sm font-medium text-gray-700">
                        {evaluation?.score || 0} / {criterion.max_score}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div 
                        className={`h-2.5 rounded-full ${
                          (evaluation?.score || 0) >= criterion.max_score * 0.8 ? 'bg-green-600' :
                          (evaluation?.score || 0) >= criterion.max_score * 0.5 ? 'bg-yellow-400' :
                          'bg-red-600'
                        }`}
                        style={{ width: `${((evaluation?.score || 0) / criterion.max_score) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ))}

      {/* Summary Section */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            Evaluation Summary
          </h3>
          
          {/* Category-wise scores */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {Object.entries(groupedCriteria).map(([category, categoryCriteria]) => {
              const categoryScore = calculateCategoryScore(category, categoryCriteria);
              const totalWeight = categoryCriteria.reduce((acc, c) => acc + c.weight, 0);

              return (
                <div key={category} className="bg-gray-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-700 capitalize">{category}</h4>
                  <div className="mt-2">
                    <div className="text-2xl font-bold text-gray-900">
                      {categoryScore.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">
                      Total weight: {totalWeight}%
                    </div>
                  </div>
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        categoryScore >= 80 ? 'bg-green-600' :
                        categoryScore >= 50 ? 'bg-yellow-400' :
                        'bg-red-600'
                      }`}
                      style={{ width: `${categoryScore}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Overall Score Display */}
          <div className="bg-blue-50 rounded-lg p-6 text-center">
            <h4 className="text-sm font-medium text-gray-700">Overall Evaluation Score</h4>
            <div className="mt-2">
              <div className="text-4xl font-bold text-gray-900">
                {calculateOverallScore().toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500 mt-1">
                Technical (70%): {(calculateCategoryScore('technical', groupedCriteria.technical || [])).toFixed(1)}% |
                Financial (30%): {(calculateCategoryScore('financial', groupedCriteria.financial || [])).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end space-x-4">
        <button
          type="button"
          className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Evaluation'}
        </button>
      </div>
    </form>
  );
};

export default TransparentEvaluationForm;