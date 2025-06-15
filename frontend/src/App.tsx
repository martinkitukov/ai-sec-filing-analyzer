import React, { useState } from 'react';
import axios from 'axios';
import FilingForm from './components/FilingForm';
import FilingResult from './components/FilingResult';

interface AnalysisResult {
  filing_id: string;
  filing_type: string;
  metadata: any;
  answer?: string;
}

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: { url: string; question?: string }) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post('http://localhost:8000/api/v1/analyze', data);
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <div className="bg-white shadow sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-8">
                SEC Insight AI
              </h1>
              
              <FilingForm onSubmit={handleSubmit} isLoading={loading} />

              {error && (
                <div className="mt-6 bg-red-50 border-l-4 border-red-400 p-4">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              {result && (
                <FilingResult
                  filingId={result.filing_id}
                  filingType={result.filing_type}
                  metadata={result.metadata}
                  answer={result.answer}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 