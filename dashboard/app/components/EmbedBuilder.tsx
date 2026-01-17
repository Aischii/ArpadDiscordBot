import React, { useState, useEffect } from 'react';

interface EmbedField {
  name: string;
  value: string;
  inline: boolean;
}

interface Embed {
  title?: string;
  description?: string;
  color?: string;
  image?: { url: string };
  thumbnail?: { url: string };
  fields?: EmbedField[];
  footer?: { text: string };
  author?: { name: string; icon_url?: string };
}

interface EmbedBuilderProps {
  embedKey: string;
  title: string;
}

export const EmbedBuilder: React.FC<EmbedBuilderProps> = ({ embedKey, title }) => {
  const [embed, setEmbed] = useState<Embed>({
    title: '',
    description: '',
    color: '#5865F2',
    fields: [],
  });
  const [jsonView, setJsonView] = useState(false);

  useEffect(() => {
    loadEmbed();
  }, [embedKey]);

  const loadEmbed = async () => {
    try {
      const response = await fetch('/api/embed');
      const data = await response.json();
      if (data[embedKey]) {
        setEmbed(data[embedKey]);
      }
    } catch (error) {
      console.error('Failed to load embed:', error);
    }
  };

  const saveEmbed = async () => {
    try {
      await fetch('/api/embed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [embedKey]: embed }),
      });
      alert('Embed saved successfully!');
    } catch (error) {
      console.error('Failed to save embed:', error);
    }
  };

  const addField = () => {
    setEmbed({
      ...embed,
      fields: [...(embed.fields || []), { name: '', value: '', inline: false }],
    });
  };

  const updateField = (index: number, field: EmbedField) => {
    const updatedFields = [...(embed.fields || [])];
    updatedFields[index] = field;
    setEmbed({ ...embed, fields: updatedFields });
  };

  const removeField = (index: number) => {
    setEmbed({
      ...embed,
      fields: (embed.fields || []).filter((_, i) => i !== index),
    });
  };

  const hexToDecimal = (hex: string) => parseInt(hex.replace('#', ''), 16);

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
        <button
          onClick={() => setJsonView(!jsonView)}
          className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded transition"
        >
          {jsonView ? 'Visual' : 'JSON'}
        </button>
      </div>

      {jsonView ? (
        <div className="space-y-3">
          <textarea
            value={JSON.stringify(embed, null, 2)}
            onChange={(e) => {
              try {
                setEmbed(JSON.parse(e.target.value));
              } catch {}
            }}
            className="w-full h-64 p-3 border border-gray-300 rounded font-mono text-sm"
          />
        </div>
      ) : (
        <>
          {/* Preview */}
          <div className="border-l-4 border-blue-500 bg-gray-50 p-4 rounded">
            <h4 className="text-sm font-semibold text-gray-600 mb-2">Preview</h4>
            <div
              className="bg-gray-900 rounded text-white p-4 max-w-sm"
              style={{ borderLeft: `4px solid ${embed.color || '#5865F2'}` }}
            >
              {embed.author && (
                <div className="flex items-center gap-2 mb-3">
                  {embed.author.icon_url && (
                    <img
                      src={embed.author.icon_url}
                      alt="author"
                      className="w-6 h-6 rounded-full"
                    />
                  )}
                  <span className="text-sm font-semibold">{embed.author.name}</span>
                </div>
              )}
              {embed.title && <h3 className="font-semibold text-lg mb-2">{embed.title}</h3>}
              {embed.description && <p className="text-sm mb-4 whitespace-pre-wrap">{embed.description}</p>}
              {embed.thumbnail?.url && (
                <img src={embed.thumbnail.url} alt="thumbnail" className="rounded mb-4 max-w-full" />
              )}
              {embed.fields?.map((field, idx) => (
                <div key={idx} className={embed.fields![idx].inline ? 'inline-block w-1/3' : 'w-full'}>
                  <p className="text-xs font-semibold mb-1">{field.name}</p>
                  <p className="text-sm mb-3 text-gray-300">{field.value}</p>
                </div>
              ))}
              {embed.image?.url && <img src={embed.image.url} alt="image" className="rounded mb-4 w-full" />}
              {embed.footer && (
                <p className="text-xs text-gray-400 mt-4 pt-4 border-t border-gray-700">{embed.footer.text}</p>
              )}
            </div>
          </div>

          {/* Editor */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={embed.title || ''}
                onChange={(e) => setEmbed({ ...embed, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                maxLength={256}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={embed.description || ''}
                onChange={(e) => setEmbed({ ...embed, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none h-24"
                maxLength={4096}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
                <input
                  type="color"
                  value={embed.color || '#5865F2'}
                  onChange={(e) => setEmbed({ ...embed, color: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Author Name</label>
                <input
                  type="text"
                  value={embed.author?.name || ''}
                  onChange={(e) =>
                    setEmbed({
                      ...embed,
                      author: { ...embed.author, name: e.target.value },
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Footer Text</label>
              <input
                type="text"
                value={embed.footer?.text || ''}
                onChange={(e) =>
                  setEmbed({
                    ...embed,
                    footer: { text: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>

            {/* Fields */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="block text-sm font-medium text-gray-700">Fields</label>
                <button
                  onClick={addField}
                  className="text-sm bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded transition"
                >
                  + Add Field
                </button>
              </div>

              {embed.fields?.map((field, idx) => (
                <div key={idx} className="border border-gray-300 p-3 rounded space-y-2">
                  <div className="flex justify-between items-start">
                    <div className="flex-1 space-y-2">
                      <input
                        type="text"
                        placeholder="Field Name"
                        value={field.name}
                        onChange={(e) => updateField(idx, { ...field, name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-200 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                        maxLength={256}
                      />
                      <textarea
                        placeholder="Field Value"
                        value={field.value}
                        onChange={(e) => updateField(idx, { ...field, value: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-200 rounded text-sm focus:ring-2 focus:ring-blue-500 outline-none h-16"
                        maxLength={1024}
                      />
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={field.inline}
                          onChange={(e) => updateField(idx, { ...field, inline: e.target.checked })}
                          className="cursor-pointer"
                        />
                        Inline
                      </label>
                    </div>
                    <button
                      onClick={() => removeField(idx)}
                      className="ml-2 text-red-500 hover:text-red-700 text-sm font-semibold"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <button
        onClick={saveEmbed}
        className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded transition"
      >
        Save Embed
      </button>
    </div>
  );
};
