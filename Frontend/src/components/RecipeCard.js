import React from 'react';
import { useNavigate } from 'react-router-dom';
import { interactionAPI } from '../services/api';
import './RecipeCard.css';

const PLACEHOLDER = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=70';

const DIFF_COLOR = { facile: '#27AE60', moyen: '#F39C12', difficile: '#E74C3C' };
const DIFF_LABEL = { facile: 'Facile', moyen: 'Moyen', difficile: 'Difficile' };

export default function RecipeCard({ recipe, reason, score, showReason = false }) {
  const nav = useNavigate();

  const handleClick = async () => {
    try {
      await interactionAPI.add({ recipe_id: recipe.id, interaction_type: 'view', score: 0.5 });
    } catch {}
    nav(`/recipe/${recipe.id}`);
  };

  const stars = Math.round(recipe.note_moyenne || 0);

  return (
    <div className="rcard animate-fade" onClick={handleClick} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && handleClick()}>
      <div className="rcard__img-wrap">
        <img
          src={recipe.image_url || PLACEHOLDER}
          alt={recipe.title}
          className="rcard__img"
          onError={e => { e.target.src = PLACEHOLDER; }}
        />
        {recipe.difficulte && (
          <span className="rcard__badge" style={{ background: DIFF_COLOR[recipe.difficulte] }}>
            {DIFF_LABEL[recipe.difficulte]}
          </span>
        )}
        {showReason && reason && (
          <span className="rcard__reason">
            {reason === 'ALS' ? 'Pour vous' : reason === 'fridge' ? 'Frigo' : reason === 'popularity' ? 'Populaire' : reason === 'content' ? 'Similaire' : reason === 'hybrid' ? 'Similaire' : reason}
          </span>
        )}
      </div>
      <div className="rcard__body">
        <p className="rcard__cuisine">{recipe.cuisine || 'Cuisine du monde'}</p>
        <h3 className="rcard__title">{recipe.title}</h3>
        {recipe.description && (
          <p className="rcard__desc">{recipe.description}</p>
        )}
        <div className="rcard__meta">
          <span className="rcard__stars">
            {'★'.repeat(stars)}{'☆'.repeat(5 - stars)}
            <span className="rcard__nb">({recipe.nb_avis})</span>
          </span>
          {recipe.temps_preparation && (
            <span className="rcard__time">{recipe.temps_preparation} min</span>
          )}
          {recipe.niveau_calorie != null && (
            <span className="rcard__calories">{recipe.niveau_calorie} kcal</span>
          )}
        </div>
        <div className="rcard__tags">
          {(recipe.tags || []).slice(0, 3).map(t => (
            <span key={t} className="rcard__tag">{t}</span>
          ))}
          {recipe.regime && <span className="rcard__tag rcard__tag--regime">{recipe.regime}</span>}
        </div>
      </div>
    </div>
  );
}