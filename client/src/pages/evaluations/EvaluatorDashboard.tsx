// client/src/pages/evaluators/EvaluatorDashboard.tsx
import React, { useState, useEffect } from 'react';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { evaluationApi } from '../../api/api';
import { Link } from 'react-router-dom';

interface PendingTask {
  tender_id: number;
  tender_reference: string;
  offer_id: number;
  vendor_name: string;
  pending_criteria: Array<{
    category: string;
    criteria: Array<{
      id: number;
      name: string;
      weight: number;
      max_score: number;
    }>;
  }>;
  total_pending: number;
  total_criteria: number;
  progress: number;
  deadline: {
    date: string;
    days_remaining: number;
    is_overdue: boolean;
  };
}

const EvaluatorDashboard: React.FC = () => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchDashboardData(),
      fetchPendingTasks()
    ]).finally(() => setLoading(false));
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await evaluationApi.getStatistics();
      setDashboardData(response);
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
    }
  };

  const fetchPendingTasks = async () => {
    try {
      const response = await evaluationApi.getPendingTasks();
      setPendingTasks(response.pending_tasks);
    } catch (err: any) {
      console.error('Error fetching pending tasks:', err);
      setError(err.message || 'Failed to load pending tasks');
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

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Evaluator Dashboard</h1>
        
        {/* Overview Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <span className="material-icons">assignment</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Total Evaluations</p>
                <p className="text-2xl font-bold text-gray-800">{dashboardData?.total_evaluations || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-orange-100 text-orange-600">
                <span className="material-icons">pending</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Pending Tasks</p>
                <p className="text-2xl font-bold text-gray-800">{pendingTasks.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-red-100 text-red-600">
                <span className="material-icons">warning</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Overdue</p>
                <p className="text-2xl font-bold text-gray-800">
                  {pendingTasks.filter(task => task.deadline.is_overdue).length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600">
                <span className="material-icons">bar_chart</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Avg. Score Given</p>
                <p className="text-2xl font-bold text-gray-800">
                  {dashboardData?.avg_score?.toFixed(1) || '0.0'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Priority Tasks Section */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Priority Evaluation Tasks</h2>
            <p className="text-sm text-gray-500 mt-1">Tenders with approaching deadlines that need evaluation</p>
          </div>
          
          {pendingTasks.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tender
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Vendor
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Progress
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Pending
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Deadline
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {pendingTasks.map((task) => (
                    <tr 
                      key={`${task.tender_id}-${task.offer_id}`} 
                      className={task.deadline.is_overdue ? 'bg-red-50' : undefined}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{task.tender_reference}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{task.vendor_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-full bg-gray-200 rounded-full h-2.5">
                            <div 
                              className="bg-blue-600 h-2.5 rounded-full" 
                              style={{ width: `${task.progress}%` }}
                            ></div>
                          </div>
                          <span className="ml-2 text-sm text-gray-500">{task.progress}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{task.total_pending} criteria</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`text-sm ${task.deadline.is_overdue ? 'text-red-600 font-medium' : 'text-gray-900'}`}>
                          {task.deadline.is_overdue ? 'Overdue' : `${task.deadline.days_remaining} days`}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link 
                          to={`/offers/${task.offer_id}/evaluate`}
                          className={`text-blue-600 hover:text-blue-900 ${task.deadline.is_overdue ? 'font-bold' : ''}`}
                        >
                          {task.deadline.is_overdue ? 'Evaluate Now!' : 'Evaluate'}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-4 text-sm text-gray-500">
              No pending evaluation tasks
            </div>
          )}
        </div>

        {/* Recent Evaluations */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Recent Evaluations</h2>
          </div>
          
          {dashboardData?.recent_evaluations?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tender
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Vendor
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Criteria
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Score
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dashboardData.recent_evaluations.map((evaluation: any) => (
                    <tr key={evaluation.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{evaluation.tender_reference}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{evaluation.vendor_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{evaluation.criteria_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{evaluation.score} / {evaluation.max_score}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {new Date(evaluation.created_at).toLocaleString()}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-4 text-sm text-gray-500">
              No recent evaluations
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Quick Actions</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Link 
                to="/evaluations"
                className="flex items-center p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <span className="material-icons text-blue-600 mr-3">list</span>
                <div>
                  <div className="font-medium text-gray-900">All Evaluations</div>
                  <div className="text-sm text-gray-600">View all evaluation tasks</div>
                </div>
              </Link>
              
              <Link 
                to="/evaluations/my-evaluations"
                className="flex items-center p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
              >
                <span className="material-icons text-green-600 mr-3">history</span>
                <div>
                  <div className="font-medium text-gray-900">My Evaluations</div>
                  <div className="text-sm text-gray-600">View your past evaluations</div>
                </div>
              </Link>
              
              <Link 
                to="/evaluations/performance"
                className="flex items-center p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
              >
                <span className="material-icons text-purple-600 mr-3">analytics</span>
                <div>
                  <div className="font-medium text-gray-900">Performance</div>
                  <div className="text-sm text-gray-600">View your evaluation metrics</div>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default EvaluatorDashboard;