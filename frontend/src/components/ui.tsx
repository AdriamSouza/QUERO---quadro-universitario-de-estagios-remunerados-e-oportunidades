import React from 'react';
import { X } from 'lucide-react';
import { Edital } from '../types/edital';
import {
  EDITAL_STATUS_LABEL, EDITAL_STATUS_STYLE, INSCRICAO_STATUS_LABEL, INSCRICAO_STATUS_STYLE,
} from '../utils/format';

export const EditalStatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${EDITAL_STATUS_STYLE[status] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
    {EDITAL_STATUS_LABEL[status] || status}
  </span>
);

export const InscricaoStatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${INSCRICAO_STATUS_STYLE[status] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
    {INSCRICAO_STATUS_LABEL[status] || status}
  </span>
);

export const PageHeader: React.FC<{ title: string; subtitle?: string; actions?: React.ReactNode }> = ({ title, subtitle, actions }) => (
  <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
    <div>
      <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">{title}</h2>
      {subtitle && <p className="mt-1.5 text-slate-600 text-sm max-w-3xl">{subtitle}</p>}
    </div>
    {actions}
  </div>
);

export const Spinner: React.FC<{ label?: string }> = ({ label }) => (
  <div className="text-center py-16">
    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto" />
    {label && <p className="mt-4 text-slate-500 text-sm">{label}</p>}
  </div>
);

export const EmptyState: React.FC<{ icon: React.ReactNode; title: string; description?: string; children?: React.ReactNode }> = ({
  icon, title, description, children,
}) => (
  <div className="text-center py-16 px-6 bg-white rounded-xl border border-slate-200">
    <div className="text-slate-400 mx-auto mb-3 flex justify-center">{icon}</div>
    <h3 className="text-base font-semibold text-slate-900">{title}</h3>
    {description && <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">{description}</p>}
    {children}
  </div>
);

export const Modal: React.FC<{
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'md' | 'lg';
}> = ({ title, subtitle, onClose, children, footer, size = 'md' }) => (
  <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto" role="dialog" aria-modal="true">
    <div className={`bg-white text-slate-900 text-left rounded-2xl shadow-xl w-full border border-slate-200 my-8 ${size === 'lg' ? 'max-w-2xl' : 'max-w-lg'}`}>
      <div className="flex items-start justify-between p-5 border-b border-slate-100">
        <div>
          <h3 className="text-lg font-bold text-slate-900">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1" aria-label="Fechar">
          <X className="h-5 w-5" />
        </button>
      </div>
      <div className="p-5">{children}</div>
      {footer && <div className="flex flex-wrap justify-end gap-2 px-5 py-4 border-t border-slate-100 bg-slate-50 rounded-b-2xl">{footer}</div>}
    </div>
  </div>
);

export const EditalSelect: React.FC<{
  editais: Edital[];
  value: number | null;
  onChange: (id: number) => void;
  label?: string;
  right?: React.ReactNode;
}> = ({ editais, value, onChange, label = 'Edital', right }) => (
  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
    <div className="w-full sm:w-auto">
      <label className="block text-xs font-semibold text-slate-500 mb-1">{label}</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full sm:w-[28rem] py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white font-medium text-slate-800"
      >
        {editais.length === 0 && <option value="">Nenhum edital disponível</option>}
        {editais.map((e) => (
          <option key={e.id} value={e.id}>
            #{e.id} — {e.titulo} ({EDITAL_STATUS_LABEL[e.status] || e.status})
          </option>
        ))}
      </select>
    </div>
    {right}
  </div>
);

export const btn = {
  primary: 'inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed',
  secondary: 'inline-flex items-center justify-center px-4 py-2 border border-slate-300 bg-white rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition disabled:opacity-50',
  danger: 'inline-flex items-center justify-center px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 transition disabled:opacity-50',
  success: 'inline-flex items-center justify-center px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 transition disabled:opacity-50',
};

export const inputClass = 'w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white text-slate-900 placeholder:text-slate-400';
