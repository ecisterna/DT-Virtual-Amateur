from neo4j import GraphDatabase

driver = GraphDatabase.driver('neo4j://127.0.0.1:7687', auth=('neo4j', 'neo4j123'))

with driver.session() as session:
    print("=== LIMPIANDO Y RECREANDO BASE DE DATOS ===\n")
    
    # Limpiar todo
    session.run('MATCH (n) DETACH DELETE n')
    print("✓ Base de datos limpiada")
    
    # Crear jugadores
    session.run("CREATE (j1:Jugador {nombre: 'Martinez', rol: 'Comun'})")
    session.run("CREATE (j2:Jugador {nombre: 'Gomez', rol: 'Capitan'})")
    session.run("CREATE (j3:Jugador {nombre: 'Perez', rol: 'Comun'})")
    print("✓ Jugadores creados")
    
    # Crear estados físicos
    session.run("CREATE (ef1:EstadoFisico {cansancio: 75, riesgoLesion: 60, minuto: 75})")
    session.run("CREATE (ef2:EstadoFisico {cansancio: 30, riesgoLesion: 10, minuto: 75})")
    session.run("CREATE (ef3:EstadoFisico {cansancio: 50, riesgoLesion: 20, minuto: 75})")
    print("✓ Estados físicos creados")
    
    # Crear recomendaciones
    session.run("CREATE (r1:Recomendacion {accion: 'Sustitucion inmediata', confianza: 0.75})")
    session.run("CREATE (r2:Recomendacion {accion: 'Mantener', confianza: 0.90})")
    session.run("CREATE (r3:Recomendacion {accion: 'Mantener con esfuerzo', confianza: 0.60})")
    print("✓ Recomendaciones creadas")
    
    # Crear partido y rival
    session.run("CREATE (p1:Partido {id: 'P01', resultado: 'Perdiendo 0-1', minuto: 75})")
    session.run("CREATE (riv1:Rival {nombre: 'Los Primos', intensidad: 'Alta'})")
    print("✓ Partido y rival creados")
    
    # Crear relaciones Jugador -> Estado -> Recomendacion (CON LOS NOMBRES CORRECTOS)
    session.run('''
        MATCH (j:Jugador {nombre: 'Martinez'}), (ef:EstadoFisico {cansancio: 75})
        CREATE (j)-[:TIENE_ESTADO]->(ef)
    ''')
    session.run('''
        MATCH (ef:EstadoFisico {cansancio: 75}), (r:Recomendacion {accion: 'Sustitucion inmediata'})
        CREATE (ef)-[:GENERA_RECOMENDACION]->(r)
    ''')
    
    session.run('''
        MATCH (j:Jugador {nombre: 'Gomez'}), (ef:EstadoFisico {cansancio: 30})
        CREATE (j)-[:TIENE_ESTADO]->(ef)
    ''')
    session.run('''
        MATCH (ef:EstadoFisico {cansancio: 30}), (r:Recomendacion {accion: 'Mantener'})
        CREATE (ef)-[:GENERA_RECOMENDACION]->(r)
    ''')
    
    session.run('''
        MATCH (j:Jugador {nombre: 'Perez'}), (ef:EstadoFisico {cansancio: 50})
        CREATE (j)-[:TIENE_ESTADO]->(ef)
    ''')
    session.run('''
        MATCH (ef:EstadoFisico {cansancio: 50}), (r:Recomendacion {accion: 'Mantener con esfuerzo'})
        CREATE (ef)-[:GENERA_RECOMENDACION]->(r)
    ''')
    print("✓ Relaciones Jugador->Estado->Recomendacion creadas")
    
    # Crear relaciones de partido
    session.run('''
        MATCH (p:Partido {id: 'P01'}), (riv:Rival {nombre: 'Los Primos'})
        CREATE (p)-[:ENFRENTA]->(riv)
    ''')
    session.run('''
        MATCH (j:Jugador {nombre: 'Martinez'}), (p:Partido {id: 'P01'})
        CREATE (j)-[:JUEGA_EN]->(p)
    ''')
    session.run('''
        MATCH (j:Jugador {nombre: 'Gomez'}), (p:Partido {id: 'P01'})
        CREATE (j)-[:JUEGA_EN]->(p)
    ''')
    session.run('''
        MATCH (j:Jugador {nombre: 'Perez'}), (p:Partido {id: 'P01'})
        CREATE (j)-[:JUEGA_EN]->(p)
    ''')
    print("✓ Relaciones de partido creadas")
    
    # Verificar Martinez
    print("\n=== VERIFICACIÓN DE MARTINEZ ===")
    result = session.run('''
        MATCH (j:Jugador {nombre: 'Martinez'})-[:TIENE_ESTADO]->(e:EstadoFisico)-[:GENERA_RECOMENDACION]->(r:Recomendacion)
        RETURN j.nombre, e.cansancio, e.riesgoLesion, r.accion
    ''')
    
    for record in result:
        print(f"Jugador: {record['j.nombre']}")
        print(f"Cansancio: {record['e.cansancio']}")
        print(f"Riesgo de lesión: {record['e.riesgoLesion']}")
        print(f"Recomendación: {record['r.accion']}")

driver.close()
print("\n✅ Base de datos configurada correctamente!")
print("\nAhora puedes probar tu aplicación preguntando:")
print("  - ¿Cuál es el cansancio de Martinez?")
print("  - ¿Qué jugadores deben ser sustituidos?")
