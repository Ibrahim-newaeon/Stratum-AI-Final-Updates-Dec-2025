/**
 * WhatsApp Contacts Manager
 * Manage WhatsApp Business contacts with import, search, and opt-in management
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UserGroupIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ArrowUpTrayIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  PhoneIcon,
  TrashIcon,
  PencilIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon,
  DocumentArrowDownIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface Contact {
  id: number;
  phone_number: string;
  country_code: string;
  display_name: string | null;
  opt_in_status: 'pending' | 'opted_in' | 'opted_out';
  message_count: number;
  last_message_at: string | null;
  created_at: string;
}

// Mock data
const mockContacts: Contact[] = [
  {
    id: 1,
    phone_number: '+1234567890',
    country_code: 'US',
    display_name: 'John Doe',
    opt_in_status: 'opted_in',
    message_count: 24,
    last_message_at: '2025-01-30T10:00:00Z',
    created_at: '2024-12-01T00:00:00Z',
  },
  {
    id: 2,
    phone_number: '+1987654321',
    country_code: 'US',
    display_name: 'Jane Smith',
    opt_in_status: 'opted_in',
    message_count: 18,
    last_message_at: '2025-01-29T15:30:00Z',
    created_at: '2024-12-05T00:00:00Z',
  },
  {
    id: 3,
    phone_number: '+447123456789',
    country_code: 'GB',
    display_name: 'Alice Johnson',
    opt_in_status: 'pending',
    message_count: 0,
    last_message_at: null,
    created_at: '2025-01-20T00:00:00Z',
  },
  {
    id: 4,
    phone_number: '+971501234567',
    country_code: 'AE',
    display_name: 'Mohammed Ali',
    opt_in_status: 'opted_in',
    message_count: 45,
    last_message_at: '2025-01-30T08:00:00Z',
    created_at: '2024-11-15T00:00:00Z',
  },
  {
    id: 5,
    phone_number: '+33612345678',
    country_code: 'FR',
    display_name: 'Pierre Dupont',
    opt_in_status: 'opted_out',
    message_count: 12,
    last_message_at: '2025-01-15T12:00:00Z',
    created_at: '2024-10-20T00:00:00Z',
  },
];

const statusConfig = {
  opted_in: {
    label: 'Opted In',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    icon: CheckCircleIcon,
  },
  pending: { label: 'Pending', color: 'text-yellow-400', bg: 'bg-yellow-500/10', icon: ClockIcon },
  opted_out: { label: 'Opted Out', color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircleIcon },
};

export default function WhatsAppContacts() {
  const [contacts, setContacts] = useState<Contact[]>(mockContacts);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedContacts, setSelectedContacts] = useState<number[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const filteredContacts = contacts.filter((contact) => {
    const matchesSearch =
      contact.phone_number.includes(search) ||
      (contact.display_name?.toLowerCase().includes(search.toLowerCase()) ?? false);
    const matchesStatus = statusFilter === 'all' || contact.opt_in_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.ceil(filteredContacts.length / pageSize);
  const paginatedContacts = filteredContacts.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleSelectAll = () => {
    if (selectedContacts.length === paginatedContacts.length) {
      setSelectedContacts([]);
    } else {
      setSelectedContacts(paginatedContacts.map((c) => c.id));
    }
  };

  const handleToggleSelect = (id: number) => {
    setSelectedContacts((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleOptIn = (id: number) => {
    setContacts((prev) =>
      prev.map((c) => (c.id === id ? { ...c, opt_in_status: 'opted_in' as const } : c))
    );
  };

  const handleOptOut = (id: number) => {
    setContacts((prev) =>
      prev.map((c) => (c.id === id ? { ...c, opt_in_status: 'opted_out' as const } : c))
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Contact Management</h2>
          <p className="text-gray-400 text-sm">
            {filteredContacts.length} contacts •{' '}
            {contacts.filter((c) => c.opt_in_status === 'opted_in').length} opted in
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
          >
            <ArrowUpTrayIcon className="w-4 h-4" />
            Import CSV
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity"
          >
            <PlusIcon className="w-4 h-4" />
            Add Contact
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by phone or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-[rgba(255,_255,_255,_0.05)] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none transition-colors"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'opted_in', 'pending', 'opted_out'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-4 py-2 rounded-xl transition-colors text-sm font-medium',
                statusFilter === status
                  ? 'bg-[#25D366] text-white'
                  : 'bg-[rgba(255,_255,_255,_0.05)] text-gray-400 hover:text-white border border-white/10'
              )}
            >
              {status === 'all' ? 'All' : statusConfig[status as keyof typeof statusConfig]?.label}
            </button>
          ))}
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedContacts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 p-4 bg-[#25D366]/10 border border-[#25D366]/20 rounded-xl"
        >
          <span className="text-sm">{selectedContacts.length} selected</span>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 text-sm bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30">
              Opt In Selected
            </button>
            <button className="px-3 py-1.5 text-sm bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30">
              Opt Out Selected
            </button>
            <button className="px-3 py-1.5 text-sm bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30">
              Export Selected
            </button>
          </div>
        </motion.div>
      )}

      {/* Contacts Table */}
      <div className="bg-[rgba(255,_255,_255,_0.05)] rounded-2xl border border-white/5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="p-4 text-left">
                  <input
                    type="checkbox"
                    checked={
                      selectedContacts.length === paginatedContacts.length &&
                      paginatedContacts.length > 0
                    }
                    onChange={handleSelectAll}
                    className="rounded border-white/20 bg-transparent"
                  />
                </th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Contact</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Phone</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Status</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Messages</th>
                <th className="p-4 text-left text-sm font-medium text-gray-400">Last Contact</th>
                <th className="p-4 text-right text-sm font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedContacts.map((contact) => {
                const status = statusConfig[contact.opt_in_status];
                const StatusIcon = status.icon;
                return (
                  <tr
                    key={contact.id}
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="p-4">
                      <input
                        type="checkbox"
                        checked={selectedContacts.includes(contact.id)}
                        onChange={() => handleToggleSelect(contact.id)}
                        className="rounded border-white/20 bg-transparent"
                      />
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#25D366] to-[#128C7E] flex items-center justify-center font-medium">
                          {contact.display_name?.[0] || contact.phone_number[1]}
                        </div>
                        <div>
                          <div className="font-medium">{contact.display_name || 'Unknown'}</div>
                          <div className="text-xs text-gray-500">{contact.country_code}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2 text-gray-300">
                        <PhoneIcon className="w-4 h-4" />
                        {contact.phone_number}
                      </div>
                    </td>
                    <td className="p-4">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                          status.bg,
                          status.color
                        )}
                      >
                        <StatusIcon className="w-3.5 h-3.5" />
                        {status.label}
                      </span>
                    </td>
                    <td className="p-4 text-gray-300">{contact.message_count}</td>
                    <td className="p-4 text-gray-400 text-sm">
                      {contact.last_message_at
                        ? new Date(contact.last_message_at).toLocaleDateString()
                        : 'Never'}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-end gap-2">
                        {contact.opt_in_status !== 'opted_in' && (
                          <button
                            onClick={() => handleOptIn(contact.id)}
                            className="p-2 text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
                            title="Opt In"
                          >
                            <CheckCircleIcon className="w-4 h-4" />
                          </button>
                        )}
                        {contact.opt_in_status !== 'opted_out' && (
                          <button
                            onClick={() => handleOptOut(contact.id)}
                            className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                            title="Opt Out"
                          >
                            <XCircleIcon className="w-4 h-4" />
                          </button>
                        )}
                        <button className="p-2 text-gray-400 hover:bg-white/5 rounded-lg transition-colors">
                          <PencilIcon className="w-4 h-4" />
                        </button>
                        <button className="p-2 text-gray-400 hover:bg-red-500/10 hover:text-red-400 rounded-lg transition-colors">
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between p-4 border-t border-white/5">
          <span className="text-sm text-gray-400">
            Showing {(currentPage - 1) * pageSize + 1}-
            {Math.min(currentPage * pageSize, filteredContacts.length)} of {filteredContacts.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-2 bg-[#1a1a24] rounded-lg disabled:opacity-50 hover:bg-[#22222e] transition-colors"
            >
              <ChevronLeftIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-2 bg-[#1a1a24] rounded-lg disabled:opacity-50 hover:bg-[#22222e] transition-colors"
            >
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Add Contact Modal */}
      <AnimatePresence>
        {showAddModal && (
          <AddContactModal
            onClose={() => setShowAddModal(false)}
            onAdd={(contact) => {
              setContacts((prev) => [{ ...contact, id: prev.length + 1 }, ...prev]);
              setShowAddModal(false);
            }}
          />
        )}
      </AnimatePresence>

      {/* Import Modal */}
      <AnimatePresence>
        {showImportModal && (
          <ImportContactsModal
            onClose={() => setShowImportModal(false)}
            onImport={(count) => {
              // Mock import
              setShowImportModal(false);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// Add Contact Modal
function AddContactModal({
  onClose,
  onAdd,
}: {
  onClose: () => void;
  onAdd: (contact: Omit<Contact, 'id'>) => void;
}) {
  const [formData, setFormData] = useState({
    phone_number: '',
    country_code: 'US',
    display_name: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      ...formData,
      opt_in_status: 'pending',
      message_count: 0,
      last_message_at: null,
      created_at: new Date().toISOString(),
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-md bg-[rgba(255,_255,_255,_0.05)] rounded-2xl border border-white/10 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold">Add Contact</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Phone Number</label>
            <input
              type="tel"
              required
              placeholder="+1234567890"
              value={formData.phone_number}
              onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
              className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Country Code</label>
            <select
              value={formData.country_code}
              onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
              className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
            >
              <option value="US">United States (+1)</option>
              <option value="GB">United Kingdom (+44)</option>
              <option value="AE">UAE (+971)</option>
              <option value="SA">Saudi Arabia (+966)</option>
              <option value="FR">France (+33)</option>
              <option value="DE">Germany (+49)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Display Name</label>
            <input
              type="text"
              placeholder="John Doe"
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity font-medium"
            >
              Add Contact
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

// Import Contacts Modal
function ImportContactsModal({
  onClose,
  onImport,
}: {
  onClose: () => void;
  onImport: (count: number) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === 'text/csv') {
      setFile(droppedFile);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-lg bg-[rgba(255,_255,_255,_0.05)] rounded-2xl border border-white/10 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold">Import Contacts</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            'border-2 border-dashed rounded-xl p-8 text-center transition-colors',
            isDragging ? 'border-[#25D366] bg-[#25D366]/5' : 'border-white/10',
            file ? 'border-green-500 bg-green-500/5' : ''
          )}
        >
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <DocumentArrowDownIcon className="w-8 h-8 text-green-400" />
              <div>
                <div className="font-medium">{file.name}</div>
                <div className="text-sm text-gray-400">{(file.size / 1024).toFixed(1)} KB</div>
              </div>
            </div>
          ) : (
            <>
              <ArrowUpTrayIcon className="w-12 h-12 mx-auto mb-4 text-gray-500" />
              <p className="text-gray-400 mb-2">Drag and drop your CSV file here</p>
              <p className="text-sm text-gray-500">or</p>
              <label className="inline-block mt-3 px-4 py-2 bg-[#25D366] rounded-lg cursor-pointer hover:opacity-90">
                Browse Files
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </label>
            </>
          )}
        </div>

        <div className="mt-4 p-4 bg-[#0b1215] rounded-xl">
          <h4 className="font-medium mb-2">CSV Format Required:</h4>
          <code className="text-sm text-gray-400">
            phone_number,country_code,display_name
            <br />
            +1234567890,US,John Doe
            <br />
            +447123456789,GB,Jane Smith
          </code>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onImport(0)}
            disabled={!file}
            className="flex-1 px-4 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity font-medium disabled:opacity-50"
          >
            Import Contacts
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
