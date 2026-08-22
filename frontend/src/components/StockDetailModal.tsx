import React from 'react';
import type { ScanResult } from '../api/scanner';
import { StockDetailView } from './StockDetailView';

interface StockDetailModalProps {
  stock: ScanResult | null;
  onClose: () => void;
}

export const StockDetailModal: React.FC<StockDetailModalProps> = ({
  stock,
  onClose,
}) => {
  if (!stock) return null;

  return (
    <StockDetailView
      stock={stock}
      onBack={onClose}
    />
  );
};
