// src/pages/evaluations/EvaluationList.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { evaluationApi } from '../../api/api';

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

const EvaluationList: React.FC = () => {
  const { user } = useAuth();
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingTasks();
  }, []);

  const fetchPendingTasks = async () => {
    try {
      setLoading(true);
      const response = await evaluationApi.getPendingTasks();
      setPendingTasks(response.pending_tasks);
    } catch (err: any) {
      console.error('Error fetching pending tasks:', err);
      setError(err.message || 'Failed to load pending tasks');
    } finally {
      setLoading(false);
    }
  };

  // Only allow evaluators to view this page
  if (user?.role !== 'evaluator' && user?.role !== 'staff' && user?.role !== 'admin') {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Access Denied</strong>
          <span className="block sm:inline"> You do not have permission to view evaluations.</span>
        </div>
      </Layout>
    );
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-900">My Evaluation Tasks</h1>
          {(user?.role === 'staff' || user?.role === 'admin') && (
            <Link
              to="/evaluations/performance"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center"
            >
              <span className="material-icons mr-2">analytics</span>
              Performance Dashboard
            </Link>
          )}
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <span className="material-icons">assignment</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Pending Offers</p>
                <p className="text-2xl font-bold text-gray-800">{pendingTasks.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-orange-100 text-orange-600">
                <span className="material-icons">pending</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Total Pending</p>
                <p className="text-2xl font-bold text-gray-800">
                  {pendingTasks.reduce((sum, task) => sum + task.total_pending, 0)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-red-100 text-red-600">
                <span className="material-icons">warning</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Overdue Tasks</p>
                <p className="text-2xl font-bold text-gray-800">
                  {pendingTasks.filter(task => task.deadline.is_overdue).length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600">
                <span className="material-icons">check_circle</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-500 font-semibold">Average Progress</p>
                <p className="text-2xl font-bold text-gray-800">
                  {pendingTasks.length > 0 
                    ? Math.round(pendingTasks.reduce((sum, task) => sum + task.progress, 0) / pendingTasks.length)
                    : 0}%
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Pending Tasks Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Pending Evaluation Tasks</h2>
          </div>
          {pendingTasks.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tender
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vendor
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pending
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Deadline
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pendingTasks.map((task) => (
                  <tr key={`${task.tender_id}-${task.offer_id}`} className={task.deadline.is_overdue ? 'bg-red-50' : undefined}>
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
                      <div className="text-sm text-gray-900">{task.total_pending} / {task.total_criteria}</div>
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
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">No pending evaluation tasks</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default EvaluationList;