import React from 'react';
import IngredientIcon from '../utils/IngredientIcon';
import './IngredientCombineAnimation.css';

export default function IngredientCombineAnimation({ items = [] }) {
  // Cap how many icons orbit the pot so it stays readable even with a
  // long ingredient list.
  const shown = items.slice(0, 8);
  const angleStep = 360 / Math.max(shown.length, 1);

  return (
    <div className="combine-wrap">
      <div className="combine-stage">
        {shown.map((item, i) => {
          const angle = angleStep * i;
          return (
            <span
              key={item.id}
              className="combine-ingredient"
              style={{
                '--angle': `${angle}deg`,
                animationDelay: `${i * 0.18}s`,
              }}
            >
              <IngredientIcon categorie={item.categorie} />
            </span>
          );
        })}

        <div className="combine-pot">
          <span className="combine-pot__steam combine-pot__steam--1" />
          <span className="combine-pot__steam combine-pot__steam--2" />
          <span className="combine-pot__steam combine-pot__steam--3" />
          <div className="combine-pot__body">
            <div className="combine-pot__bubble" />
          </div>
          <div className="combine-pot__lid" />
        </div>
      </div>

      <p className="combine-text">
        Votre plat mijote
        <span className="combine-dots"><span>.</span><span>.</span><span>.</span></span>
      </p>
    </div>
  );
}