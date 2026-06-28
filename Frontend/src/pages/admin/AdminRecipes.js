import React, { useState, useEffect } from 'react';
import { adminAPI, ingredientAPI, recipeAPI } from '../../services/api';
import AdminLayout from '../../components/AdminLayout';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import './AdminRecipes.css';

const EMPTY_FORM = {
  title: '', description: '', instructions: '', cuisine: '', regime: 'normal',
  difficulte: 'moyen', temps_preparation: '', niveau_calorie: '', tags: '',
  image_url: '', is_published: true, ingredients: [],
};

function RecipeFormModal({ initial, onClose, onSaved }) {
  const [form, setForm] = useState(initial ? { ...EMPTY_FORM, ...initial, ingredients: initial.ingredients || [] } : EMPTY_FORM);
  const [ingSearch, setIngSearch] = useState('');
  const [ingResults, setIngResults] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  useEffect(() => {
    if (!ingSearch.trim()) { setIngResults([]); return; }
    const t = setTimeout(() => ingredientAPI.list(ingSearch, 15).then(setIngResults).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [ingSearch]);

  const addIngredient = item => {
    if (form.ingredients.some(i => i.ingredient_id === item.id)) return;
    setForm(f => ({ ...f, ingredients: [...f.ingredients, { ingredient_id: item.id, name: item.name, quantite: '', unite: item.unite_standard || '' }] }));
    setIngSearch(''); setIngResults([]);
  };

  const updateIngredientField = (id, field, value) => {
    setForm(f => ({
      ...f,
      ingredients: f.ingredients.map(i => (i.ingredient_id === id ? { ...i, [field]: value } : i)),
    }));
  };

  const removeIngredient = id => {
    setForm(f => ({ ...f, ingredients: f.ingredients.filter(i => i.ingredient_id !== id) }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const payload = {
      ...form,
      temps_preparation: form.temps_preparation ? Number(form.temps_preparation) : null,
      niveau_calorie: form.niveau_calorie ? Number(form.niveau_calorie) : null,
      tags: typeof form.tags === 'string' ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : form.tags,
      ingredients: form.ingredients.map(i => ({
        ingredient_id: i.ingredient_id,
        quantite: i.quantite ? Number(i.quantite) : null,
        unite: i.unite || null,
      })),
    };
    try {
      if (initial?.id) {
        await adminAPI.updateRecipe(initial.id, payload);
      } else {
        await adminAPI.createRecipe(payload);
      }
      onSaved();
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="arecipes-modal-backdrop" onClick={onClose}>
      <div className="arecipes-modal" onClick={e => e.stopPropagation()}>
        <div className="arecipes-modal__header">
          <h2>{initial?.id ? 'Modifier la recette' : 'Nouvelle recette'}</h2>
          <button className="arecipes-modal__close" onClick={onClose}>×</button>
        </div>

        <form className="arecipes-form" onSubmit={handleSubmit}>
          <Input label="Titre" value={form.title} onChange={set('title')} required />

          <div className="arecipes-field">
            <label>Description</label>
            <textarea rows={2} value={form.description || ''} onChange={set('description')} />
          </div>

          <div className="arecipes-field">
            <label>Instructions (une étape par ligne)</label>
            <textarea rows={5} value={form.instructions || ''} onChange={set('instructions')} />
          </div>

          <div className="arecipes-grid">
            <Input label="Cuisine" placeholder="ex: Marocaine" value={form.cuisine || ''} onChange={set('cuisine')} />
            <div className="arecipes-field">
              <label>Régime</label>
              <select value={form.regime || 'normal'} onChange={set('regime')}>
                <option value="normal">normal</option>
                <option value="végétarien">végétarien</option>
                <option value="végétalien">végétalien</option>
                <option value="sans gluten">sans gluten</option>
              </select>
            </div>
            <div className="arecipes-field">
              <label>Difficulté</label>
              <select value={form.difficulte || 'moyen'} onChange={set('difficulte')}>
                <option value="facile">facile</option>
                <option value="moyen">moyen</option>
                <option value="difficile">difficile</option>
              </select>
            </div>
            <Input label="Temps (min)" type="number" value={form.temps_preparation || ''} onChange={set('temps_preparation')} />
            <Input label="Calories" type="number" value={form.niveau_calorie || ''} onChange={set('niveau_calorie')} />
            <Input label="Tags (séparés par virgules)" value={Array.isArray(form.tags) ? form.tags.join(', ') : (form.tags || '')} onChange={set('tags')} />
          </div>

          <Input label="URL de l'image" placeholder="https://…" value={form.image_url || ''} onChange={set('image_url')} />

          <div className="arecipes-field">
            <label>Ingrédients</label>
            <div className="arecipes-ing-search-wrap">
              <input
                placeholder="Rechercher un ingrédient à ajouter…"
                value={ingSearch}
                onChange={e => setIngSearch(e.target.value)}
              />
              {ingResults.length > 0 && (
                <div className="arecipes-ing-dropdown">
                  {ingResults.map(item => (
                    <button type="button" key={item.id} onClick={() => addIngredient(item)}>{item.name}</button>
                  ))}
                </div>
              )}
            </div>

            <div className="arecipes-ing-list">
              {form.ingredients.map(i => (
                <div key={i.ingredient_id} className="arecipes-ing-row">
                  <span className="arecipes-ing-name">{i.name || `#${i.ingredient_id}`}</span>
                  <input
                    className="arecipes-ing-qty"
                    placeholder="qté"
                    value={i.quantite}
                    onChange={e => updateIngredientField(i.ingredient_id, 'quantite', e.target.value)}
                  />
                  <input
                    className="arecipes-ing-unit"
                    placeholder="unité"
                    value={i.unite}
                    onChange={e => updateIngredientField(i.ingredient_id, 'unite', e.target.value)}
                  />
                  <button type="button" className="arecipes-ing-rm" onClick={() => removeIngredient(i.ingredient_id)}>×</button>
                </div>
              ))}
              {form.ingredients.length === 0 && <p className="arecipes-ing-empty">Aucun ingrédient ajouté.</p>}
            </div>
          </div>

          <label className="arecipes-checkbox">
            <input type="checkbox" checked={!!form.is_published} onChange={e => setForm(f => ({ ...f, is_published: e.target.checked }))} />
            Publiée (visible côté client)
          </label>

          {error && <div className="arecipes-error">{error}</div>}

          <div className="arecipes-modal__footer">
            <Button type="button" variant="ghost" onClick={onClose}>Annuler</Button>
            <Button type="submit" variant="primary" loading={saving}>Enregistrer</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminRecipes() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    adminAPI.listRecipes().then(setRecipes).catch(() => setError('Erreur de chargement')).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const remove = async id => {
    if (!window.confirm('Supprimer définitivement cette recette ?')) return;
    try {
      await adminAPI.deleteRecipe(id);
      setRecipes(prev => prev.filter(r => r.id !== id));
    } catch {
      setError('Suppression impossible');
    }
  };

  const openCreate = () => { setEditing(null); setModalOpen(true); };
  const openEdit = async r => {
    try {
      const detail = await recipeAPI.detail(r.id);
      setEditing({
        ...detail,
        ingredients: (detail.ingredients || []).map(ri => ({
          ingredient_id: ri.ingredient.id,
          name: ri.ingredient.name,
          quantite: ri.quantite ?? '',
          unite: ri.unite || '',
        })),
      });
    } catch {
      // Fall back to the summary row we already have (no ingredients)
      // rather than blocking the edit entirely.
      setEditing({ ...r, ingredients: r.ingredients || [] });
    }
    setModalOpen(true);
  };
  const closeModal = () => setModalOpen(false);
  const onSaved = () => { setModalOpen(false); load(); };

  const filtered = recipes.filter(r => r.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <AdminLayout>
      <div className="arecipes-header">
        <div>
          <h1 className="arecipes-title">Recettes</h1>
          <p className="arecipes-sub">{recipes.length} recette(s) au total</p>
        </div>
        <div className="arecipes-header-actions">
          <input className="arecipes-search" placeholder="Rechercher…" value={search} onChange={e => setSearch(e.target.value)} />
          <Button variant="primary" onClick={openCreate}>+ Nouvelle recette</Button>
        </div>
      </div>

      {error && <div className="arecipes-error">{error}</div>}

      <div className="arecipes-table-wrap">
        {loading ? (
          <div className="arecipes-loading"><div className="spinner spinner-lg" /></div>
        ) : (
          <table className="arecipes-table">
            <thead>
              <tr>
                <th>Titre</th>
                <th>Cuisine</th>
                <th>Difficulté</th>
                <th>Note</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.id}>
                  <td className="arecipes-title-cell">{r.title}</td>
                  <td>{r.cuisine || '—'}</td>
                  <td>{r.difficulte}</td>
                  <td>{(r.note_moyenne || 0).toFixed(1)} ({r.nb_avis || 0})</td>
                  <td>
                    <span className={`arecipes-status ${r.is_published ? 'arecipes-status--pub' : 'arecipes-status--draft'}`}>
                      {r.is_published ? 'Publiée' : 'Brouillon'}
                    </span>
                  </td>
                  <td className="arecipes-actions">
                    <button className="arecipes-btn" onClick={() => openEdit(r)}>Modifier</button>
                    <button className="arecipes-btn arecipes-btn--danger" onClick={() => remove(r.id)}>Supprimer</button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="arecipes-empty">Aucune recette trouvée.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {modalOpen && <RecipeFormModal initial={editing} onClose={closeModal} onSaved={onSaved} />}
    </AdminLayout>
  );
}