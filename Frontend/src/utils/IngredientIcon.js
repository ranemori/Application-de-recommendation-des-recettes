import React from 'react';
import {
  Carrot, Apple, Beef, Fish, Milk, Wheat, Leaf, Soup, Drumstick, Salad, Utensils,
} from 'lucide-react';

const ICONS = {
  legumes: Carrot,
  fruits: Apple,
  viande: Drumstick,
  poisson: Fish,
  laitier: Milk,
  cereales: Wheat,
  epices: Leaf,
  condiments: Soup,
  legumineuses: Salad,
  autre: Utensils,
};

const CATEGORY_KEY = {
  'légumes': 'legumes', 'légume': 'legumes',
  'fruits': 'fruits', 'fruit': 'fruits',
  'viande': 'viande', 'viandes': 'viande',
  'poisson': 'poisson', 'poissons': 'poisson', 'fruits de mer': 'poisson',
  'produits laitiers': 'laitier', 'laitier': 'laitier', 'produits laitiers végétaux': 'laitier',
  'céréales': 'cereales', 'féculents': 'cereales',
  'épices': 'epices', 'épice': 'epices', 'aromates': 'epices', 'herbes': 'epices',
  'condiments': 'condiments', 'sauces': 'condiments',
  'légumineuses': 'legumineuses',
  'charcuterie': 'viande',
  'matières grasses': 'condiments',
  'levure': 'cereales',
};

export function keyForCategorie(categorie) {
  return CATEGORY_KEY[(categorie || '').toLowerCase()] || 'autre';
}

/* <IngredientIcon categorie="légumes" /> — renders the matching icon. */
export default function IngredientIcon({ categorie, className, size = 22 }) {
  const key = keyForCategorie(categorie);
  const Icon = ICONS[key] || Utensils;
  return (
    <span className={className}>
      <Icon size={size} strokeWidth={1.8} />
    </span>
  );
}