import React, { useState } from 'react';
import axios from 'axios';

interface FilingFormProps {
  onSubmit: (data: { url: string; question?: string }) => void;
  isLoading: boolean;
}

const FilingForm: React.FC<FilingFormProps> = ({ onSubmit, isLoading }) => {
  const [url, setUrl] = useState('');
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ url, question: question || undefined });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="url" className="block text-sm font-medium text-gray-700">
          EDGAR Filing URL
        </label>
        <div className="mt-1">
          <input
            type="url"
            name="url"
            id="url"
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            placeholder="https://www.sec.gov/Archives/edgar/data/..."
          />
        </div>
      </div>

      <div>
        <label htmlFor="question" className="block text-sm font-medium text-gray-700">
          Question (Optional)
        </label>
        <div className="mt-1">
          <textarea
            id="question"
            name="question"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            placeholder="Ask a question about the filing..."
          />
        </div>
      </div>

      <div>
        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isLoading ? 'Analyzing...' : 'Analyze Filing'}
        </button>
      </div>
    </form>
  );
};

export default FilingForm; 