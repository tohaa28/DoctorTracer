// SPDX-License-Identifier: MIT
export function icon(kind){const alias={palette:'fixed',quality:'high',alpha:'fixed',white:'two'};return '<img class="choice-icon" alt="" src="'+new URL('./desktop-icons/'+(alias[kind]||kind)+'.png',import.meta.url).href+'">';}
