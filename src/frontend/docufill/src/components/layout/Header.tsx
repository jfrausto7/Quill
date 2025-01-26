'use client';

import React from 'react';
import { FileText } from 'lucide-react';
import ThemeToggle from '../ThemeToggle';

interface HeaderProps {
  onLogoClick?: () => void;
}

const Header = ({ onLogoClick }: HeaderProps) => {
  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center">
          <button 
            onClick={onLogoClick}
            className="flex items-center group hover:opacity-80 transition-opacity"
          >
            <FileText className="h-8 w-8 text-blue-500 dark:text-blue-400 mr-3" />
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">DocuFill</h1>
          </button>
          <nav className="flex items-center space-x-4">
            <button className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
              Documents
            </button>
            <button className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
              History
            </button>
            <button className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600">
              Upload
            </button>
            <ThemeToggle />
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;