import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { recipeAPI, interactionAPI, recommendAPI, commentAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import ClientNavbar from '../../components/ClientNavbar';
import RecipeCard from '../../components/RecipeCard';
import Button from '../../components/ui/Button';
import Loader from '../../components/ui/Loader';
import ShareMenu from '../../components/ShareMenu';
import './RecipeDetailPage.css';

const PLACEHOLDER = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&q=70';
const DIFF_COLOR = { facile: '#27AE60', moyen: '#F39C12', difficile: '#E74C3C' };
const COMMENT_EMOJIS = ['😋', '😍', '👍', '🔥', '😅', '🤤', '😢', '🤢', '👎', '🙏', '🌶️', '⭐'];

export default function RecipeDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [recipe, setRecipe] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [liked, setLiked] = useState(false);
  const [saved, setSaved] = useState(false);
  const [rating, setRating] = useState(0);
  const [hoverStar, setHoverStar] = useState(0);
  const [ratingDone, setRatingDone] = useState(false);
  const [comments, setComments] = useState([]);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [postingComment, setPostingComment] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const commentInputRef = React.useRef(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      recipeAPI.detail(id),
      recommendAPI.similar(id, 4).catch(() => []),
    ]).then(([r, sim]) => {
      setRecipe(r);
      setSimilar(sim);
      interactionAPI.add({ recipe_id: +id, interaction_type: 'view', score: 0.5 }).catch(() => {});
    }).finally(() => setLoading(false));
    loadComments();
  }, [id]);

  const loadComments = () => {
    setCommentsLoading(true);
    commentAPI.list(id).then(setComments).catch(() => setComments([])).finally(() => setCommentsLoading(false));
  };

  const handlePostComment = async () => {
    if (!newComment.trim()) return;
    setPostingComment(true);
    try {
      const created = await commentAPI.add(+id, newComment.trim());
      setComments(prev => [created, ...prev]);
      setNewComment('');
    } catch {
      // silently ignore — could surface a toast here
    } finally {
      setPostingComment(false);
    }
  };

  const handleDeleteComment = async commentId => {
    try {
      await commentAPI.remove(commentId);
      setComments(prev => prev.filter(c => c.id !== commentId));
    } catch {}
  };

  const insertEmoji = emoji => {
    const el = commentInputRef.current;
    if (!el) {
      setNewComment(prev => prev + emoji);
      return;
    }
    const start = el.selectionStart ?? newComment.length;
    const end = el.selectionEnd ?? newComment.length;
    const next = newComment.slice(0, start) + emoji + newComment.slice(end);
    setNewComment(next);
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + emoji.length;
      el.setSelectionRange(pos, pos);
    });
  };

  const handleLike = async () => {
    setLiked(!liked);
    await interactionAPI.add({ recipe_id: +id, interaction_type: 'like', score: liked ? 0 : 1 }).catch(() => {});
  };

  const handleSave = async () => {
    setSaved(!saved);
    await interactionAPI.add({ recipe_id: +id, interaction_type: 'save', score: saved ? 0 : 1 }).catch(() => {});
  };

  const handleRate = async star => {
    setRating(star);
    setRatingDone(true);
    await interactionAPI.add({ recipe_id: +id, interaction_type: 'rating', score: star / 5 }).catch(() => {});
  };

  if (loading) return (
    <div className="rdetail-layout">
      <ClientNavbar />
      <div className="rdetail-loading"><Loader label="Préparation de la recette…" /></div>
    </div>
  );

  if (!recipe) return (
    <div className="rdetail-layout">
      <ClientNavbar />
      <div className="rdetail-loading"><p>Recette introuvable.</p><Button onClick={() => nav(-1)}> Retour</Button></div>
    </div>
  );

  const instructions = recipe.instructions ? recipe.instructions.split('\n').filter(l => l.trim()) : [];

  return (
    <div className="rdetail-layout">
      <ClientNavbar />
      <main className="rdetail-main">
        {/* Back */}
        <button className="rdetail-back" onClick={() => nav(-1)}> Retour</button>

        {/* Hero image */}
        <div className="rdetail-hero">
          <img src={recipe.image_url || PLACEHOLDER} alt={recipe.title} className="rdetail-img"
            onError={e => { e.target.src = PLACEHOLDER; }} />
          <div className="rdetail-hero-overlay">
            <div className="rdetail-hero-inner">
              {recipe.cuisine && <span className="rdetail-cuisine">{recipe.cuisine}</span>}
              <h1 className="rdetail-title">{recipe.title}</h1>
              {recipe.description && <p className="rdetail-desc">{recipe.description}</p>}
              {/* Quick actions */}
              <div className="rdetail-actions">
                <label className="like-toggle">
                  <input
                    type="checkbox"
                    className="like-toggle__check"
                    checked={liked}
                    onChange={handleLike}
                  />
                  <div className="like-toggle__container">
                    <svg className="like-toggle__icon like-toggle__icon--inactive" viewBox="0 0 24 24">
                      <path d="M12 21s-7.5-4.6-10.2-9.3C.2 8.7 1.4 5 5 4.2c2.2-.5 4.2.6 5.4 2.3a1 1 0 0 0 1.2 0C12.8 4.8 14.8 3.7 17 4.2c3.6.8 4.8 4.5 3.2 7.5C19.5 16.4 12 21 12 21z" stroke="white" strokeWidth="1.6" fill="none"/>
                    </svg>
                    <svg className="like-toggle__icon like-toggle__icon--active" viewBox="0 0 24 24">
                      <path d="M12 21s-7.5-4.6-10.2-9.3C.2 8.7 1.4 5 5 4.2c2.2-.5 4.2.6 5.4 2.3a1 1 0 0 0 1.2 0C12.8 4.8 14.8 3.7 17 4.2c3.6.8 4.8 4.5 3.2 7.5C19.5 16.4 12 21 12 21z"/>
                    </svg>
                    <span className="like-toggle__text">{liked ? 'Aimé' : 'Aimer'}</span>
                  </div>
                </label>

                <label className="save-toggle">
                  <input
                    type="checkbox"
                    className="save-toggle__check"
                    checked={saved}
                    onChange={handleSave}
                  />
                  <div className="save-toggle__container">
                    <svg className="save-toggle__icon save-toggle__icon--inactive" viewBox="0 0 24 24">
                      <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" stroke="white" strokeWidth="1.6" fill="none"/>
                    </svg>
                    <svg className="save-toggle__icon save-toggle__icon--active" viewBox="0 0 24 24">
                      <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/>
                    </svg>
                    <span className="save-toggle__text">{saved ? 'Sauvegardé' : 'Sauvegarder'}</span>
                  </div>
                </label>

                <ShareMenu url={window.location.href} title={recipe.title} />
              </div>
            </div>
          </div>
        </div>

        {/* Content grid */}
        <div className="rdetail-grid">
          {/* Left: meta + ingredients */}
          <aside className="rdetail-aside">
            {/* Meta cards */}
            <div className="rdetail-meta-cards">
              {recipe.difficulte && (
                <div className="rdetail-meta-card">
                  <span className="rdetail-meta-label">Difficulté</span>
                  <span className="rdetail-meta-val" style={{ color: DIFF_COLOR[recipe.difficulte] }}>
                    {recipe.difficulte}
                  </span>
                </div>
              )}
              {recipe.temps_preparation && (
                <div className="rdetail-meta-card">
                  <span className="rdetail-meta-label">Préparation</span>
                  <span className="rdetail-meta-val">{recipe.temps_preparation} min</span>
                </div>
              )}
              {recipe.niveau_calorie != null && (
                <div className="rdetail-meta-card">
                  <span className="rdetail-meta-label">Calories</span>
                  <span className="rdetail-meta-val">{recipe.niveau_calorie} kcal</span>
                </div>
              )}
              {recipe.note_moyenne > 0 && (
                <div className="rdetail-meta-card">
                  <span className="rdetail-meta-label">Note</span>
                  <span className="rdetail-meta-val">{recipe.note_moyenne.toFixed(1)} ({recipe.nb_avis})</span>
                </div>
              )}
              {recipe.regime && (
                <div className="rdetail-meta-card">
                  <span className="rdetail-meta-label">Régime</span>
                  <span className="rdetail-meta-val">{recipe.regime}</span>
                </div>
              )}
            </div>

            {/* Tags */}
            {(recipe.tags || []).length > 0 && (
              <div className="rdetail-tags">
                {recipe.tags.map(t => <span key={t} className="rdetail-tag">{t}</span>)}
              </div>
            )}

            {/* Ingredients */}
            <div className="rdetail-ingredients">
              <h3 className="rdetail-section-title">Ingrédients</h3>
              {(recipe.ingredients || []).length === 0
                ? <p className="rdetail-no-ing">Aucun ingrédient listé.</p>
                : <ul className="rdetail-ing-list">
                    {recipe.ingredients.map(ri => (
                      <li key={ri.ingredient.id} className="rdetail-ing-item">
                        <span className="rdetail-ing-name">{ri.ingredient.name}</span>
                        {ri.quantite && <span className="rdetail-ing-qty">{ri.quantite} {ri.unite || ''}</span>}
                      </li>
                    ))}
                  </ul>
              }
            </div>

            {/* Rating */}
            <div className="rdetail-rating-box">
              <h3 className="rdetail-section-title">Votre note</h3>
              {ratingDone
                ? <p className="rdetail-rating-done">Merci pour votre note de {rating}/5 ! Notre IA prend cela en compte.</p>
                : <div className="rdetail-stars">
                    {[1,2,3,4,5].map(s => (
                      <button key={s} className={`rdetail-star ${s <= (hoverStar || rating) ? 'rdetail-star--active' : ''}`}
                        onMouseEnter={() => setHoverStar(s)} onMouseLeave={() => setHoverStar(0)}
                        onClick={() => handleRate(s)}>★</button>
                    ))}
                    <span className="rdetail-star-hint">{hoverStar || rating ? `${hoverStar || rating}/5` : 'Cliquez pour noter'}</span>
                  </div>
              }
            </div>
          </aside>

          {/* Right: instructions */}
          <div className="rdetail-content">
            <h2 className="rdetail-section-title">Instructions</h2>
            {instructions.length === 0
              ? <p className="rdetail-no-ing">Aucune instruction disponible.</p>
              : <ol className="rdetail-instructions">
                  {instructions.map((step, i) => (
                    <li key={i} className="rdetail-step">
                      <div className="rdetail-step-num">{i + 1}</div>
                      <p className="rdetail-step-text">{step}</p>
                    </li>
                  ))}
                </ol>
            }

            {/* Similar recipes */}
            {similar.length > 0 && (
              <div className="rdetail-similar">
                <h2 className="rdetail-section-title" style={{ marginBottom: '1rem' }}>Recettes similaires</h2>
                <div className="rdetail-similar-grid">
                  {similar.map(r => <RecipeCard key={r.recipe?.id || r.id} recipe={r.recipe || r} showReason={!!r.reason} reason={r.reason} />)}
                </div>
              </div>
            )}

            {/* Comments */}
            <div className="rdetail-comments">
              <h2 className="rdetail-section-title" style={{ marginBottom: '1rem' }}>
                Commentaires{comments.length > 0 ? ` (${comments.length})` : ''}
              </h2>

              {commentsLoading ? (
                <p className="rdetail-no-ing">Chargement des commentaires…</p>
              ) : comments.length === 0 ? (
                <p className="rdetail-no-ing">Aucun commentaire pour le moment. Soyez le premier à donner votre avis !</p>
              ) : (
                <div className="cmt-list">
                  {comments.map(c => (
                    <div key={c.id} className="cmt-card">
                      <div className="cmt-card__avatar">
                        {c.user?.avatar_url
                          ? <img src={c.user.avatar_url} alt="" className="cmt-card__avatar-img" />
                          : (c.user?.username || 'U')[0].toUpperCase()
                        }
                      </div>
                      <div className="cmt-card__body">
                        <div className="cmt-card__head">
                          <span className="cmt-card__name">{c.user?.username || 'Utilisateur'}</span>
                          <span className="cmt-card__date">
                            {new Date(c.created_at).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
                          </span>
                          {user && (user.id === c.user?.id || user.role === 'admin') && (
                            <button className="cmt-card__delete" onClick={() => handleDeleteComment(c.id)}>
                              Supprimer
                            </button>
                          )}
                        </div>
                        <p className="cmt-card__text">{c.content}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="cmt-box">
                <div className="cmt-box__inner">
                  <textarea
                    ref={commentInputRef}
                    className="cmt-box__textarea"
                    placeholder="Partagez votre avis sur cette recette…"
                    value={newComment}
                    onChange={e => setNewComment(e.target.value)}
                    rows={2}
                    maxLength={2000}
                  />

                  {showEmojiPicker && (
                    <div className="cmt-emoji-picker">
                      {COMMENT_EMOJIS.map(em => (
                        <button
                          key={em}
                          type="button"
                          className="cmt-emoji-btn"
                          onClick={() => insertEmoji(em)}
                        >
                          {em}
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="cmt-box__actions">
                    <button
                      type="button"
                      className={`cmt-box__icon-btn ${showEmojiPicker ? 'cmt-box__icon-btn--active' : ''}`}
                      onClick={() => setShowEmojiPicker(v => !v)}
                      aria-label="Ajouter un emoji"
                      title="Emoji"
                    >
                      😊
                    </button>
                    <button
                      type="button"
                      className="cmt-box__send"
                      onClick={handlePostComment}
                      disabled={!newComment.trim() || postingComment}
                      aria-label="Publier"
                      title="Publier"
                    >
                      {postingComment ? (
                        <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                      ) : (
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                          <path strokeLinejoin="round" strokeLinecap="round" strokeWidth="2.5" stroke="#fff" d="M12 5L12 20" />
                          <path strokeLinejoin="round" strokeLinecap="round" strokeWidth="2.5" stroke="#fff" d="M7 9L11.2929 4.70711C11.6262 4.37377 11.7929 4.20711 12 4.20711C12.2071 4.20711 12.3738 4.37377 12.7071 4.70711L17 9" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}