'use client';

import React from 'react';
import { FileText } from 'lucide-react';

interface DocumentSelectorProps {
  documents: Array<{
    _id: string;
    name: string;
    type: string;
  }>;
  selectedDocuments: string[];
  onSelectionChange: (ids: string[]) => void;
}

const DocumentSelector = ({
  documents,
  selectedDocuments,
  onSelectionChange,
}: DocumentSelectorProps) => {
  const toggleDocument = (id: string) => {
    if (selectedDocuments.includes(id)) {
      onSelectionChange(selectedDocuments.filter(docId => docId !== id));
    } else {
      onSelectionChange([...selectedDocuments, id]);
    }
  };

  const randomId = () => Math.random().toString(36).substring(7);

  return React.createElement(
    'aside',
    {
      key: `document-selector-${randomId()}`,
      className: "bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 w-64 p-4"
    },
    [
      React.createElement(
        'h3',
        {
          key: `header-${randomId()}`,
          className: "font-semibold text-gray-900 dark:text-white mb-4"
        },
        'Referenced Documents'
      ),
      React.createElement(
        'ul',
        {
          key: `document-list-${randomId()}`,
          className: "space-y-2"
        },
        documents.length === 0 
          ? React.createElement(
              'li',
              {
                key: `empty-message-${randomId()}`,
                className: "text-sm text-gray-500 dark:text-gray-400 text-center"
              },
              'No documents available'
            )
          : documents.map(doc => 
              React.createElement(
                'li',
                {
                  key: `doc-${doc._id}-${randomId()}`,
                  className: "mb-2"
                },
                React.createElement(
                  'label',
                  {
                    key: `label-${doc._id}-${randomId()}`,
                    className: "flex items-center space-x-2 cursor-pointer p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  },
                  [
                    React.createElement('input', {
                      key: `checkbox-${doc._id}-${randomId()}`,
                      type: "checkbox",
                      checked: selectedDocuments.includes(doc._id),
                      onChange: () => toggleDocument(doc._id),
                      className: "rounded border-gray-300 dark:border-gray-600"
                    }),
                    React.createElement(FileText, {
                      key: `icon-${doc._id}-${randomId()}`,
                      className: "h-4 w-4 text-gray-500 dark:text-gray-400"
                    }),
                    React.createElement(
                      'span',
                      {
                        key: `text-${doc._id}-${randomId()}`,
                        className: "text-sm text-gray-700 dark:text-gray-300"
                      },
                      doc.name
                    )
                  ]
                )
              )
            )
      )
    ]
  );
};

export default DocumentSelector;