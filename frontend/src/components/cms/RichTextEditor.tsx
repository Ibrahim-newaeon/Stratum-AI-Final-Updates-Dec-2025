/**
 * Stratum AI - Rich Text Editor Component
 *
 * TipTap-based WYSIWYG editor with toolbar for headings, formatting, lists, links, and images.
 * Outputs both HTML and JSON formats for storage.
 */

import { EditorContent, useEditor } from '@tiptap/react';
import { BubbleMenu } from '@tiptap/react/menus';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';
import { useCallback, useEffect } from 'react';
import {
  Bold,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Image as ImageIcon,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Minus,
  Quote,
  Redo,
  RemoveFormatting,
  Strikethrough,
  Undo,
} from 'lucide-react';

interface RichTextEditorProps {
  content?: string;
  contentJson?: Record<string, unknown>;
  onChange?: (html: string, json: Record<string, unknown>) => void;
  placeholder?: string;
  className?: string;
  editable?: boolean;
}

const MenuButton = ({
  onClick,
  isActive = false,
  disabled = false,
  children,
  title,
}: {
  onClick: () => void;
  isActive?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  title: string;
}) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    title={title}
    className={`p-2 rounded hover:bg-neutral-800 transition-colors ${
      isActive ? 'bg-neutral-800 text-white' : 'text-neutral-400'
    } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
  >
    {children}
  </button>
);

const Divider = () => <div className="w-px h-6 bg-neutral-700 mx-1" />;

export function RichTextEditor({
  content = '',
  contentJson,
  onChange,
  placeholder = 'Start writing...',
  className = '',
  editable = true,
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-blue-400 hover:text-blue-300 underline',
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: 'max-w-full h-auto rounded-lg my-4',
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content: contentJson || content,
    editable,
    onUpdate: ({ editor }) => {
      if (onChange) {
        const html = editor.getHTML();
        const json = editor.getJSON();
        onChange(html, json as Record<string, unknown>);
      }
    },
    editorProps: {
      attributes: {
        class:
          'prose prose-invert prose-sm sm:prose-base max-w-none focus:outline-none min-h-[300px] p-4',
      },
    },
  });

  // Update content when prop changes
  useEffect(() => {
    if (editor && contentJson && JSON.stringify(editor.getJSON()) !== JSON.stringify(contentJson)) {
      editor.commands.setContent(contentJson);
    }
  }, [editor, contentJson]);

  const setLink = useCallback(() => {
    if (!editor) return;

    const previousUrl = editor.getAttributes('link').href;
    const url = window.prompt('Enter URL:', previousUrl);

    if (url === null) return;

    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }

    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  }, [editor]);

  const addImage = useCallback(() => {
    if (!editor) return;

    const url = window.prompt('Enter image URL:');

    if (url) {
      editor.chain().focus().setImage({ src: url }).run();
    }
  }, [editor]);

  if (!editor) {
    return (
      <div className={`border border-neutral-800 rounded-lg bg-neutral-900 ${className}`}>
        <div className="p-4 text-neutral-500">Loading editor...</div>
      </div>
    );
  }

  return (
    <div
      className={`border border-neutral-800 rounded-lg bg-neutral-900 overflow-hidden ${className}`}
    >
      {/* Toolbar */}
      {editable && (
        <div className="flex flex-wrap items-center gap-1 p-2 border-b border-neutral-800 bg-neutral-900/50">
          {/* Undo/Redo */}
          <MenuButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Undo"
          >
            <Undo className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Redo"
          >
            <Redo className="w-4 h-4" />
          </MenuButton>

          <Divider />

          {/* Headings */}
          <MenuButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
            isActive={editor.isActive('heading', { level: 1 })}
            title="Heading 1"
          >
            <Heading1 className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            isActive={editor.isActive('heading', { level: 2 })}
            title="Heading 2"
          >
            <Heading2 className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            isActive={editor.isActive('heading', { level: 3 })}
            title="Heading 3"
          >
            <Heading3 className="w-4 h-4" />
          </MenuButton>

          <Divider />

          {/* Text Formatting */}
          <MenuButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            isActive={editor.isActive('bold')}
            title="Bold"
          >
            <Bold className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            isActive={editor.isActive('italic')}
            title="Italic"
          >
            <Italic className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleStrike().run()}
            isActive={editor.isActive('strike')}
            title="Strikethrough"
          >
            <Strikethrough className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleCode().run()}
            isActive={editor.isActive('code')}
            title="Inline Code"
          >
            <Code className="w-4 h-4" />
          </MenuButton>

          <Divider />

          {/* Lists */}
          <MenuButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            isActive={editor.isActive('bulletList')}
            title="Bullet List"
          >
            <List className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            isActive={editor.isActive('orderedList')}
            title="Numbered List"
          >
            <ListOrdered className="w-4 h-4" />
          </MenuButton>

          <Divider />

          {/* Block Elements */}
          <MenuButton
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            isActive={editor.isActive('blockquote')}
            title="Quote"
          >
            <Quote className="w-4 h-4" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            title="Horizontal Rule"
          >
            <Minus className="w-4 h-4" />
          </MenuButton>

          <Divider />

          {/* Link & Image */}
          <MenuButton onClick={setLink} isActive={editor.isActive('link')} title="Add Link">
            <LinkIcon className="w-4 h-4" />
          </MenuButton>
          <MenuButton onClick={addImage} title="Add Image">
            <ImageIcon className="w-4 h-4" />
          </MenuButton>

          <Divider />

          {/* Clear Formatting */}
          <MenuButton
            onClick={() => editor.chain().focus().unsetAllMarks().clearNodes().run()}
            title="Clear Formatting"
          >
            <RemoveFormatting className="w-4 h-4" />
          </MenuButton>
        </div>
      )}

      {/* Bubble Menu (appears on text selection) */}
      {editable && (
        <BubbleMenu
          editor={editor}
          tippyOptions={{ duration: 100 }}
          className="flex items-center gap-1 p-1 bg-neutral-800 border border-neutral-700 rounded-lg shadow-lg"
        >
          <MenuButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            isActive={editor.isActive('bold')}
            title="Bold"
          >
            <Bold className="w-3 h-3" />
          </MenuButton>
          <MenuButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            isActive={editor.isActive('italic')}
            title="Italic"
          >
            <Italic className="w-3 h-3" />
          </MenuButton>
          <MenuButton onClick={setLink} isActive={editor.isActive('link')} title="Add Link">
            <LinkIcon className="w-3 h-3" />
          </MenuButton>
        </BubbleMenu>
      )}

      {/* Editor Content */}
      <EditorContent editor={editor} />
    </div>
  );
}

export default RichTextEditor;
