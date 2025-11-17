// Script corregido para Neo4j con las relaciones correctas
// Limpiar la base de datos para pruebas
MATCH (n) DETACH DELETE n;

// 1. Crear Nodos de Jugadores
CREATE (j1:Jugador {nombre: 'Martinez', rol: 'Comun'});
CREATE (j2:Jugador {nombre: 'Gomez', rol: 'Capitan'});
CREATE (j3:Jugador {nombre: 'Perez', rol: 'Comun'});

// 2. Crear Nodos de EstadoFisico (Datos que vendrían del módulo de lógica difusa)
CREATE (ef1:EstadoFisico {cansancio: 75, riesgoLesion: 60, minuto: 75});
CREATE (ef2:EstadoFisico {cansancio: 30, riesgoLesion: 10, minuto: 75});
CREATE (ef3:EstadoFisico {cansancio: 50, riesgoLesion: 20, minuto: 75});

// 3. Crear Nodos de Recomendacion (Resultados de la inferencia)
CREATE (r1:Recomendacion {accion: 'Sustitucion inmediata', confianza: 0.75});
CREATE (r2:Recomendacion {accion: 'Mantener', confianza: 0.90});
CREATE (r3:Recomendacion {accion: 'Mantener con esfuerzo', confianza: 0.60});

// 4. Crear Nodos de Partido y Rival
CREATE (p1:Partido {id: 'P01', resultado: 'Perdiendo 0-1', minuto: 75});
CREATE (riv1:Rival {nombre: 'Los Primos', intensidad: 'Alta'});

// 5. Crear Relaciones (CON LOS NOMBRES CORRECTOS SEGÚN app.py)
// Relaciones Jugador -> Estado -> Recomendacion
MATCH (j1:Jugador {nombre: 'Martinez'}), (ef1:EstadoFisico {cansancio: 75})
CREATE (j1)-[:TIENE_ESTADO]->(ef1);

MATCH (ef1:EstadoFisico {cansancio: 75}), (r1:Recomendacion {accion: 'Sustitucion inmediata'})
CREATE (ef1)-[:GENERA_RECOMENDACION]->(r1);

MATCH (j2:Jugador {nombre: 'Gomez'}), (ef2:EstadoFisico {cansancio: 30})
CREATE (j2)-[:TIENE_ESTADO]->(ef2);

MATCH (ef2:EstadoFisico {cansancio: 30}), (r2:Recomendacion {accion: 'Mantener'})
CREATE (ef2)-[:GENERA_RECOMENDACION]->(r2);

MATCH (j3:Jugador {nombre: 'Perez'}), (ef3:EstadoFisico {cansancio: 50})
CREATE (j3)-[:TIENE_ESTADO]->(ef3);

MATCH (ef3:EstadoFisico {cansancio: 50}), (r3:Recomendacion {accion: 'Mantener con esfuerzo'})
CREATE (ef3)-[:GENERA_RECOMENDACION]->(r3);

// Relaciones de Partido
MATCH (p1:Partido {id: 'P01'}), (riv1:Rival {nombre: 'Los Primos'})
CREATE (p1)-[:ENFRENTA]->(riv1);

MATCH (j1:Jugador {nombre: 'Martinez'}), (p1:Partido {id: 'P01'})
CREATE (j1)-[:JUEGA_EN]->(p1);

MATCH (j2:Jugador {nombre: 'Gomez'}), (p1:Partido {id: 'P01'})
CREATE (j2)-[:JUEGA_EN]->(p1);

MATCH (j3:Jugador {nombre: 'Perez'}), (p1:Partido {id: 'P01'})
CREATE (j3)-[:JUEGA_EN]->(p1);
