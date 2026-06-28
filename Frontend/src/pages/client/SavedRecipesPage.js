import React, { useState, useEffect } from 'react';
import { userAPI } from '../../services/api';
import RecipeCard from '../../components/RecipeCard';
import ClientNavbar from '../../components/ClientNavbar';
import Loader from '../../components/ui/Loader';
import './RecipesPage.css';
import './SavedRecipesPage.css';

export default function SavedRecipesPage() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    userAPI.saved().then(setRecipes).catch(() => setRecipes([])).finally(() => setLoading(false));
  }, []);

  return (
    <div className="rlist-layout">
      <ClientNavbar />
      <main className="rlist-main">
        <div className="rlist-header">
          <h1 className="rlist-title">Recettes sauvegardées</h1>
          <p className="rlist-sub">
            {loading ? 'Chargement…' : `${recipes.length} recette(s) sauvegardée(s)`}
          </p>
        </div>

        {loading ? (
          <div className="saved-loading"><Loader label="Récupération de vos favoris…" /></div>
        ) : recipes.length > 0 ? (
          <div className="rlist-grid">
            {recipes.map((r, i) => (
              <div key={r.id} className="animate-fade" style={{ animationDelay: `${Math.min(i * 0.03, 0.5)}s` }}>
                <RecipeCard recipe={r} />
              </div>
            ))}
          </div>
        ) : (
          <div className="rlist-empty">
            <p>Vous n'avez encore sauvegardé aucune recette.</p>
            <p className="saved-empty-hint">
              Cliquez sur "Sauvegarder" sur une recette pour la retrouver ici.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}