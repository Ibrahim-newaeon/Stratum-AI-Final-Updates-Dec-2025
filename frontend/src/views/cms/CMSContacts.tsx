/**
 * CMS Contact Submissions
 * View and manage contact form submissions
 */

import { useState } from 'react';
import {
  EnvelopeIcon,
  EnvelopeOpenIcon,
  ChatBubbleLeftIcon,
  ExclamationTriangleIcon,
  FunnelIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import {
  CMSContact,
  ContactFilters,
  useAdminContacts,
  useMarkContactRead,
  useMarkContactResponded,
  useMarkContactSpam,
} from '@/api/cms';

export default function CMSContacts() {
  const [filters, setFilters] = useState<ContactFilters>({
    page: 1,
    page_size: 20,
    exclude_spam: true,
  });
  const [selectedContact, setSelectedContact] = useState<CMSContact | null>(null);
  const [responseNotes, setResponseNotes] = useState('');

  const { data, isLoading } = useAdminContacts(filters);
  const markReadMutation = useMarkContactRead();
  const markRespondedMutation = useMarkContactResponded();
  const markSpamMutation = useMarkContactSpam();

  const contacts = data?.contacts || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / (filters.page_size || 20));

  const openDetail = (contact: CMSContact) => {
    setSelectedContact(contact);
    setResponseNotes(contact.response_notes || '');
    if (!contact.is_read) {
      markReadMutation.mutate({ id: contact.id, isRead: true });
    }
  };

  const handleMarkResponded = () => {
    if (!selectedContact) return;
    markRespondedMutation.mutate(
      { id: selectedContact.id, isResponded: true, responseNotes },
      {
        onSuccess: () => {
          setSelectedContact(null);
        },
      }
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Contact Submissions</h1>
          <p className="text-white/60 mt-1">{total} message{total !== 1 ? 's' : ''}</p>
        </div>
      </div>

      {/* Filter Toggles */}
      <div className="flex gap-3">
        <button
          onClick={() =>
            setFilters((f) => ({
              ...f,
              unread_only: !f.unread_only,
              page: 1,
            }))
          }
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filters.unread_only
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
              : 'bg-white/5 border border-white/10 text-white/60 hover:text-white'
          }`}
        >
          <FunnelIcon className="w-4 h-4" />
          Unread Only
        </button>
        <button
          onClick={() =>
            setFilters((f) => ({
              ...f,
              exclude_spam: !f.exclude_spam,
              page: 1,
            }))
          }
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            !filters.exclude_spam
              ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
              : 'bg-white/5 border border-white/10 text-white/60 hover:text-white'
          }`}
        >
          <ExclamationTriangleIcon className="w-4 h-4" />
          {filters.exclude_spam ? 'Show Spam' : 'Showing Spam'}
        </button>
      </div>

      {/* Messages List */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
          </div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-20">
            <EnvelopeIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60">No messages found</p>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {contacts.map((contact) => (
              <button
                key={contact.id}
                onClick={() => openDetail(contact)}
                className={`w-full text-left px-6 py-4 hover:bg-white/5 transition-colors ${!contact.is_read ? 'bg-purple-500/5' : ''}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="mt-0.5">
                      {contact.is_read ? (
                        <EnvelopeOpenIcon className="w-5 h-5 text-white/30" />
                      ) : (
                        <EnvelopeIcon className="w-5 h-5 text-purple-400" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-medium ${!contact.is_read ? 'text-white' : 'text-white/80'}`}
                        >
                          {contact.name}
                        </span>
                        {contact.is_spam && (
                          <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded-full">
                            Spam
                          </span>
                        )}
                        {contact.is_responded && (
                          <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">
                            Responded
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-white/50">
                        {contact.email}
                        {contact.company && ` \u2022 ${contact.company}`}
                      </p>
                      {contact.subject && (
                        <p className="text-sm text-white/70 mt-1 font-medium">{contact.subject}</p>
                      )}
                      <p className="text-sm text-white/40 mt-1 line-clamp-2">{contact.message}</p>
                    </div>
                  </div>
                  <span className="text-xs text-white/30 whitespace-nowrap flex-shrink-0">
                    {new Date(contact.created_at).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-white/50">
            Page {filters.page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) - 1 }))}
              disabled={filters.page === 1}
              className="px-3 py-1.5 text-sm bg-white/5 border border-white/10 rounded-lg text-white/60 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) + 1 }))}
              disabled={filters.page === totalPages}
              className="px-3 py-1.5 text-sm bg-white/5 border border-white/10 rounded-lg text-white/60 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">Message from {selectedContact.name}</h2>
              <button
                onClick={() => setSelectedContact(null)}
                className="p-2 text-white/40 hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Contact info */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-white/5 rounded-xl">
                <div>
                  <p className="text-xs text-white/40 mb-1">Name</p>
                  <p className="text-white font-medium">{selectedContact.name}</p>
                </div>
                <div>
                  <p className="text-xs text-white/40 mb-1">Email</p>
                  <p className="text-white">{selectedContact.email}</p>
                </div>
                {selectedContact.company && (
                  <div>
                    <p className="text-xs text-white/40 mb-1">Company</p>
                    <p className="text-white">{selectedContact.company}</p>
                  </div>
                )}
                {selectedContact.phone && (
                  <div>
                    <p className="text-xs text-white/40 mb-1">Phone</p>
                    <p className="text-white">{selectedContact.phone}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-white/40 mb-1">Received</p>
                  <p className="text-white">
                    {new Date(selectedContact.created_at).toLocaleString()}
                  </p>
                </div>
                {selectedContact.source_page && (
                  <div>
                    <p className="text-xs text-white/40 mb-1">Source Page</p>
                    <p className="text-white">{selectedContact.source_page}</p>
                  </div>
                )}
              </div>

              {/* Subject */}
              {selectedContact.subject && (
                <div>
                  <p className="text-xs text-white/40 mb-1">Subject</p>
                  <p className="text-white font-medium">{selectedContact.subject}</p>
                </div>
              )}

              {/* Message */}
              <div>
                <p className="text-xs text-white/40 mb-2">Message</p>
                <div className="p-4 bg-white/5 rounded-xl text-white/80 whitespace-pre-wrap">
                  {selectedContact.message}
                </div>
              </div>

              {/* Response Notes */}
              <div>
                <label className="block text-xs text-white/40 mb-2">Response Notes</label>
                <textarea
                  value={responseNotes}
                  onChange={(e) => setResponseNotes(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="Add notes about your response..."
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between p-4 border-t border-white/10">
              <button
                onClick={() =>
                  markSpamMutation.mutate(
                    { id: selectedContact.id, isSpam: !selectedContact.is_spam },
                    { onSuccess: () => setSelectedContact(null) }
                  )
                }
                className="flex items-center gap-2 px-3 py-2 text-sm text-orange-400 hover:bg-orange-500/10 rounded-lg transition-colors"
              >
                <ExclamationTriangleIcon className="w-4 h-4" />
                {selectedContact.is_spam ? 'Not Spam' : 'Mark as Spam'}
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => setSelectedContact(null)}
                  className="px-4 py-2 text-white/60 hover:text-white"
                >
                  Close
                </button>
                {!selectedContact.is_responded && (
                  <button
                    onClick={handleMarkResponded}
                    disabled={markRespondedMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    <ChatBubbleLeftIcon className="w-4 h-4" />
                    {markRespondedMutation.isPending ? 'Saving...' : 'Mark Responded'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
