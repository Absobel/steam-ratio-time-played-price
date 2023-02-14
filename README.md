# steam-rapport-heure-de-jeu-prix
Trie les jeux d'un user steam par rapport heure de jeu prix. Si vous avez plus de 200 entrées dans votre bibliothèque, ça va prendre beaucoup plus de temps parce que l'api de steam limite les appels.

# Pour que ça marche
Faut mettre ça dans un terminal.
``` pip install -r requirements.txt ```

# TODO
- [x] Tenter au lieu de faire un appel toutes les deux sec de faire en sorte de, quand l'api renvoie null, de faire un appel toutes les 10 (ou autre nombre) sec jusqu'à ce que ça remarche.
- [x] Faire en sorte que le résultat soit envoyé dans un fichier (c'est simple à faire mais flemme)
- [ ] Ajouter debugging (messages d'erreurs quand jeu prix inconnu)