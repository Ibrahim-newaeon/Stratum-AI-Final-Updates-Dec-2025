/**
 * CMS Post Editor View
 * Wrapper view for creating/editing posts using the PostEditor component
 */

import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { PostEditor } from '@/components/cms/PostEditor';
import {
  useAdminPost,
  useAdminCategories,
  useAdminAuthors,
  useAdminTags,
  useCreatePost,
  useUpdatePost,
  PostCreate,
  PostUpdate,
} from '@/api/cms';

export default function CMSPostEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;

  const { data: post, isLoading: postLoading } = useAdminPost(id || '');
  const { data: categoriesData } = useAdminCategories();
  const { data: authorsData } = useAdminAuthors();
  const { data: tagsData } = useAdminTags();

  const createMutation = useCreatePost();
  const updateMutation = useUpdatePost();

  const categories = categoriesData?.categories || [];
  const authors = authorsData?.authors || [];
  const tags = tagsData?.tags || [];

  const handleSave = (data: PostCreate | PostUpdate) => {
    if (isEditing && id) {
      updateMutation.mutate(
        { id, data: data as PostUpdate },
        { onSuccess: () => navigate('/cms/posts') }
      );
    } else {
      createMutation.mutate(data as PostCreate, {
        onSuccess: () => navigate('/cms/posts'),
      });
    }
  };

  if (isEditing && postLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <button
        onClick={() => navigate('/cms/posts')}
        className="flex items-center gap-2 text-white/60 hover:text-white transition-colors"
      >
        <ArrowLeftIcon className="w-4 h-4" />
        Back to Posts
      </button>

      <PostEditor
        post={isEditing ? post : undefined}
        categories={categories}
        authors={authors}
        tags={tags}
        onSave={handleSave}
        onCancel={() => navigate('/cms/posts')}
        isLoading={createMutation.isPending || updateMutation.isPending}
        inline
      />
    </div>
  );
}
