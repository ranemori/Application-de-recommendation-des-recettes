import React, { useState, useEffect, useRef } from 'react';
import { ingredientAPI, userAPI, recommendAPI } from '../../services/api';
import RecipeCard from '../../components/RecipeCard';
import ClientNavbar from '../../components/ClientNavbar';
import Button from '../../components/ui/Button';
import LottiePlayer from '../../components/LottiePlayer';
import cookingAnimation from '../../assets/lottie/Cooking.json';
import appleBuddy from '../../assets/images/apple-buddy.gif';
import carrotBuddy from '../../assets/images/carrot-buddy.gif';
import pearBuddy from '../../assets/images/pear-buddy.gif';
import strawberryBuddy from '../../assets/images/strawberry-buddy.gif';
import IngredientCombineAnimation from '../../components/IngredientCombineAnimation';
import IngredientIcon from '../../utils/IngredientIcon';
import './FridgePage.css';

export default function FridgePage() {
  const [allIngredients, setAllIngredients] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [recs, setRecs] = useState([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [saved, setSaved] = useState(false);
  const [strict, setStrict] = useState(true);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);
  const searchRef = useRef(null);

  /* Load the full ingredient catalog once, for the browsable card grid */
  useEffect(() => {
    ingredientAPI.list('', 200).then(setAllIngredients).catch(() => {});
  }, []);

  /* Load saved fridge on mount */
  useEffect(() => {
    userAPI.getFridge().then(data => {
      const items = data.ingredients || [];
      setSelectedItems(items);
      setSelectedIds(items.map(i => i.id));
    }).catch(() => {});
  }, []);

  const addIngredient = item => {
    if (selectedIds.includes(item.id)) return;
    setSelectedIds(p => [...p, item.id]);
    setSelectedItems(p => [...p, item]);
    setSearch('');
    setSaved(false);
  };

  const removeIngredient = id => {
    setSelectedIds(p => p.filter(i => i !== id));
    setSelectedItems(p => p.filter(i => i.id !== id));
    setSaved(false);
  };

  const toggleIngredient = item => {
    if (selectedIds.includes(item.id)) removeIngredient(item.id);
    else addIngredient(item);
  };

  const visibleCatalog = (search.trim()
    ? allIngredients.filter(i => i.name.toLowerCase().includes(search.trim().toLowerCase()))
    : allIngredients
  ).slice(0, 60);

  const saveFridge = async () => {
    setLoadingSave(true);
    try {
      await userAPI.setFridge({ ingredient_ids: selectedIds });
      setSaved(true);
    } catch { setError('Erreur lors de la sauvegarde'); }
    finally { setLoadingSave(false); }
  };

  const findRecipes = async () => {
    if (selectedIds.length === 0) { setError('Ajoutez au moins un ingrédient'); return; }
    setError('');
    setLoadingRecs(true);
    setSearched(true);
    const startedAt = Date.now();
    const MIN_ANIMATION_MS = 1800; // let the "ingredients combine" animation play out at least once
    try {
      const data = await recommendAPI.fridge({ ingredient_ids: selectedIds, strict });
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_ANIMATION_MS) {
        await new Promise(res => setTimeout(res, MIN_ANIMATION_MS - elapsed));
      }
      setRecs(data);
    } catch { setError('Erreur lors de la recherche de recettes'); }
    finally { setLoadingRecs(false); }
  };

  const CATEGORIES = [...new Set(selectedItems.map(i => i.categorie || 'Autre'))];

  return (
    <div className="fridge-layout">
      <ClientNavbar />
      <main className="fridge-main">
        <div className="fridge-header">
          <div>
            <h1 className="fridge-title">Mon Frigo</h1>
            <p className="fridge-sub">Entrez les ingrédients disponibles chez vous — notre IA trouvera les recettes que vous pouvez cuisiner maintenant.</p>
          </div>
        </div>

        <div className="fridge-body">
          {/* Left: ingredient selector */}
          <div className="fridge-selector">
            <div className="fridge-search-box">
              <div className="fridge-search-wrap">
                <input
                  ref={searchRef}
                  className="fridge-search-input"
                  placeholder="Rechercher un ingrédient... (tomates, poulet, farine...)"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
                {search && <button className="fridge-clear-btn" onClick={() => setSearch('')}></button>}
              </div>

              {/* Browsable ingredient cards — click to select/deselect */}
              <div className="fridge-ing-grid">
                {visibleCatalog.map(item => {
                  const isSelected = selectedIds.includes(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`fridge-ing-card ${isSelected ? 'fridge-ing-card--selected' : ''}`}
                      onClick={() => toggleIngredient(item)}
                    >
                      <div className="fridge-ing-card__content">
                        <IngredientIcon categorie={item.categorie} className="fridge-ing-card__icon" />
                        <p className="fridge-ing-card__name">{item.name}</p>
                        {item.categorie && <p className="fridge-ing-card__cat">{item.categorie}</p>}
                        <span className="fridge-ing-card__check">{isSelected ? '✓ sélectionné' : '+ ajouter'}</span>
                      </div>
                    </button>
                  );
                })}
                {visibleCatalog.length === 0 && (
                  <p className="fridge-ing-empty">Aucun ingrédient ne correspond à "{search}".</p>
                )}
              </div>
            </div>

            {/* Selected ingredients */}
            <div className="fridge-selected">
              <div className="fridge-selected-header">
                <h3>Ingrédients sélectionnés</h3>
                <span className="fridge-count">{selectedIds.length} ingrédient(s)</span>
              </div>

              {selectedItems.length === 0 ? (
                <div className="fridge-empty-sel">
                  <span></span>
                  <p>Aucun ingrédient sélectionné.<br />Recherchez ci-dessus pour commencer.</p>
                </div>
              ) : (
                <div className="fridge-chips">
                  {selectedItems.map(item => (
                    <div key={item.id} className="fridge-chip">
                      <span className="fridge-chip__name">{item.name}</span>
                      {item.categorie && <span className="fridge-chip__cat">{item.categorie}</span>}
                      <button className="fridge-chip__rm" onClick={() => removeIngredient(item.id)}></button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Options */}
            <div className="fridge-options">
              <label className="fridge-option">
                <input type="checkbox" checked={strict} onChange={e => setStrict(e.target.checked)} />
                <div>
                  <strong>Mode strict</strong>
                  <span>Uniquement les recettes réalisables avec exactement vos ingrédients (sans achats supplémentaires)</span>
                </div>
              </label>
              {!strict && (
                <div className="fridge-option-info">
                  Mode relaxé : recettes avec la meilleure couverture d'ingrédients.
                </div>
              )}
            </div>

            {error && <div className="fridge-error">{error}</div>}

            {/* Actions */}
            <div className="fridge-actions">
              <Button variant="outline" onClick={saveFridge} loading={loadingSave} disabled={selectedIds.length === 0}>
                {saved ? 'Frigo sauvegardé' : 'Sauvegarder mon frigo'}
              </Button>
              <Button variant="primary" size="lg" onClick={findRecipes} loading={loadingRecs} disabled={selectedIds.length === 0}>
                Trouver des recettes
              </Button>
            </div>
          </div>

          {/* Right: recipe results */}
          <div className="fridge-results">
            {!searched && !loadingRecs && (
              <div className="fridge-results-placeholder">
                <img src={appleBuddy} alt="" className="fridge-placeholder-buddy fridge-placeholder-buddy--tl" />
                <img src={carrotBuddy} alt="" className="fridge-placeholder-buddy fridge-placeholder-buddy--tr" />
                <img src={pearBuddy} alt="" className="fridge-placeholder-buddy fridge-placeholder-buddy--bl" />
                <img src={strawberryBuddy} alt="" className="fridge-placeholder-buddy fridge-placeholder-buddy--br" />
                <div className="fridge-results-placeholder__lottie">
                  <LottiePlayer animationData={cookingAnimation} loop autoplay />
                </div>
                <h3>Vos recettes apparaîtront ici</h3>
                <p>Sélectionnez vos ingrédients disponibles et cliquez sur "Trouver des recettes".</p>
              </div>
            )}

            {loadingRecs && (
              <div className="fridge-loading">
                <IngredientCombineAnimation items={selectedItems} />
              </div>
            )}

            {!loadingRecs && searched && (
              <>
                <div className="fridge-results-header">
                  <h2 className="fridge-results-title">
                    {recs.length > 0
                      ? `${recs.length} recette(s) trouvée(s)`
                      : 'Aucune recette trouvée'}
                  </h2>
                  {recs.length === 0 && !strict && (
                    <p className="fridge-no-results">Essayez d'ajouter plus d'ingrédients ou de désactiver le mode strict.</p>
                  )}
                  {recs.length === 0 && strict && (
                    <p className="fridge-no-results">
                      Aucune recette ne peut être préparée uniquement avec ces ingrédients.
                      Essayez le <button className="fridge-no-results-btn" onClick={() => { setStrict(false); findRecipes(); }}>mode relaxé</button> pour voir les meilleures correspondances.
                    </p>
                  )}
                </div>
                {recs.length > 0 && (
                  <div className="fridge-recs-grid">
                    {recs.map((r, i) => (
                      <div key={r.recipe.id} className="animate-fade" style={{ animationDelay: `${i * 0.04}s` }}>
                        <RecipeCard {...r} showReason />
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}