# steam-rapport-heure-de-jeu-prix
Trie les jeux d'un user steam par rapport heure de jeu prix. Si vous avez plus de 200 entrées dans votre bibliothèque, ça va prendre beaucoup plus de temps parce que l'api de steam limite les appels.

# Pour que ça marche
Faut mettre ça dans un terminal.
``` pip install -r requirements.txt ```

# TODO
- [ ] Ajouter meilleur debugging (messages d'erreurs quand jeu prix inconnu)
- [ ] Faire un truc pour la clef api et remettre le truc public
- [ ] Ajouter les dlc (maybe avec https://store.steampowered.com/dynamicstore/userdata mais ça devient complexe)
- [ ] Réduire le nombre d'appels
- [ ] Mettre les trucs en anglais et réécrire au propre