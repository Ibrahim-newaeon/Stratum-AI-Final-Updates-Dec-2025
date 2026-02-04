/**
 * Neural Network Background Component
 * Dense animated background with 15 pulsing nodes and 10 connection lines
 * Part of Stratum AI Dashboard Theme (NN/g Glassmorphism Compliant)
 */

import { memo } from 'react';

export const NeuralNetworkBg = memo(function NeuralNetworkBg() {
  return (
    <div
      className="neural-network-bg"
      aria-hidden="true"
    >
      {/* 15 Neural Nodes */}
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />
      <div className="neural-node" />

      {/* 10 Connection Lines */}
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />
      <div className="neural-line" />

      {/* Circuit Grid Overlay */}
      <div className="circuit-grid" />

      {/* Gradient Accents */}
      <div
        className="absolute top-0 left-0 w-[600px] h-[600px]"
        style={{
          background: 'radial-gradient(ellipse at 0% 0%, rgba(212, 175, 55, 0.08), transparent 70%)',
        }}
      />
      <div
        className="absolute bottom-0 right-0 w-[500px] h-[500px]"
        style={{
          background: 'radial-gradient(ellipse at 100% 100%, rgba(139, 92, 246, 0.06), transparent 70%)',
        }}
      />
      <div
        className="absolute top-1/2 right-0 w-[400px] h-[400px] -translate-y-1/2"
        style={{
          background: 'radial-gradient(ellipse at 100% 50%, rgba(34, 197, 94, 0.04), transparent 70%)',
        }}
      />
    </div>
  );
});

export default NeuralNetworkBg;
