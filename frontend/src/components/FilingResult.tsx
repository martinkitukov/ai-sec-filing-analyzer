import React from 'react';

interface FilingResultProps {
  filingId: string;
  filingType: string;
  metadata: any;
  answer?: string;
}

const FilingResult: React.FC<FilingResultProps> = ({
  filingId,
  filingType,
  metadata,
  answer
}) => {
  return (
    <div className="mt-6 space-y-6">
      <div className="bg-gray-50 p-4 rounded-md">
        <h3 className="text-lg font-medium text-gray-900">Filing Information</h3>
        <dl className="mt-2 grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-gray-500">Filing ID</dt>
            <dd className="mt-1 text-sm text-gray-900">{filingId}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Filing Type</dt>
            <dd className="mt-1 text-sm text-gray-900">{filingType}</dd>
          </div>
        </dl>
      </div>

      <div className="bg-gray-50 p-4 rounded-md">
        <h3 className="text-lg font-medium text-gray-900">Metadata</h3>
        <pre className="mt-2 text-sm text-gray-700 overflow-auto">
          {JSON.stringify(metadata, null, 2)}
        </pre>
      </div>

      {answer && (
        <div className="bg-gray-50 p-4 rounded-md">
          <h3 className="text-lg font-medium text-gray-900">Answer</h3>
          <p className="mt-2 text-sm text-gray-700">{answer}</p>
        </div>
      )}
    </div>
  );
};

export default FilingResult; 