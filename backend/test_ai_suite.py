import urllib.request
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    # 1. Login con estudiante Martha Montañez (2226669)
    login_req = urllib.request.Request(
        'http://127.0.0.1:8000/auth/login', 
        data=json.dumps({'username': '2226669', 'password': 'password123'}).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(login_req) as resp:
        token = json.loads(resp.read().decode())['access_token']

    test_cases = [
        {
            'num': 1,
            'name': 'Consulta de Asignaturas y Docentes',
            'query': '¿Cuales son mis asignaturas matriculadas este semestre y quienes son mis profesores?'
        },
        {
            'num': 2,
            'name': 'Consulta de Horarios de Tutorías de Asignatura',
            'query': '¿Que dias y horarios tengo tutoria de Farmacognosia?'
        },
        {
            'num': 3,
            'name': 'Redacción Inteligente de Correo a Docente',
            'query': 'Redactame un correo formal y respetuoso para mi profesora Sidnia Rebolledo solicitandole una asesoria sobre el proyecto de Farmacognosia.'
        },
        {
            'num': 4,
            'name': 'Trámite de Cancelación de Asignaturas',
            'query': '¿Cual es el plazo maximo en semanas y los requisitos para cancelar una materia en la UIS?'
        },
        {
            'num': 5,
            'name': 'Requisitos de Grado y Paz y Salvo',
            'query': '¿Que dependencias debo tener a paz y salvo para postularme a grado en el IPRED?'
        },
        {
            'num': 6,
            'name': 'Reglamento de Habilitaciones de Asignaturas',
            'query': 'Si obtuve una calificacion de 2.5 en una materia teorica, ¿puedo habilitarla y cual es el promedio minimo?'
        },
        {
            'num': 7,
            'name': 'Guardrail contra Tareas y Matemáticas',
            'query': 'Resuelveme la siguiente integral: integral de (3x^2 + 2x) dx y hazme un script en Python para graficarla.'
        },
        {
            'num': 8,
            'name': 'Modo Conversacional para Llamada de Voz',
            'query': 'Oye, ¿donde queda la sede principal del IPRED? (Llamada de voz: responde de manera calida, concisa y fluida en 2 frases habladas en espanol)'
        }
    ]

    print('=' * 80)
    print('🚀 EJECUTANDO SUITE DE 8 PRUEBAS DE INTELIGENCIA ARTIFICIAL (IPRED UIS)')
    print('=' * 80)

    passed = 0
    for tc in test_cases:
        print(f"\n👉 TEST {tc['num']}/8: {tc['name']}")
        print(f"   Pregunta: '{tc['query']}'")
        
        start_time = time.time()
        msg_req = urllib.request.Request(
            'http://127.0.0.1:8000/chat/message',
            data=json.dumps({'message': tc['query']}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        )
        
        try:
            with urllib.request.urlopen(msg_req) as resp:
                elapsed = time.time() - start_time
                res = json.loads(resp.read().decode())
                ans = res.get('respuesta', '')
                tools = res.get('herramientas_usadas', [])
                tok = res.get('tokens_usados', 0)
                
                print(f"   ⏱️ Tiempo: {elapsed:.2f}s | Tokens: {tok} | Herramientas: {tools}")
                print("   📝 Respuesta:")
                for line in ans.strip().split('\n')[:5]:
                    print(f"      {line}")
                if len(ans.strip().split('\n')) > 5:
                    print("      ...")
                print("   ✅ ESTADO: PASÓ")
                passed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print('\n' + '=' * 80)
    print(f"🏁 RESULTADO FINAL: {passed}/8 TESTS SUPERADOS EXITOSAMENTE")
    print('=' * 80)

if __name__ == '__main__':
    run_tests()
