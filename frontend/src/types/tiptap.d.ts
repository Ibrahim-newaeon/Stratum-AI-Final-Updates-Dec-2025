import type { ComponentType, FC } from 'react';
import type { Editor, Extension, UseEditorOptions } from '@tiptap/core';

declare module '@tiptap/react' {
  export const EditorContent: FC<{ editor: Editor | null; className?: string }>;
  export function useEditor(options: UseEditorOptions): Editor | null;
}
declare module '@tiptap/react/menus' {
  export const BubbleMenu: FC<{ editor: Editor | null; children?: React.ReactNode }>;
}
declare module '@tiptap/starter-kit' {
  const StarterKit: Extension;
  export default StarterKit;
}
declare module '@tiptap/extension-link' {
  const Link: Extension;
  export default Link;
}
declare module '@tiptap/extension-image' {
  const Image: Extension;
  export default Image;
}
declare module '@tiptap/extension-placeholder' {
  const Placeholder: Extension;
  export default Placeholder;
}
