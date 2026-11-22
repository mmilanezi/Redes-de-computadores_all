# Roteiro da apresentação – Trabalho II

Gerado por `scripts/gerar_apresentacao.py` a partir das notas dos slides (edite lá e gere de novo).
Tempo previsto: **14 min 15 s** para 15 min de apresentação. O tempo ao lado de cada slide é a meta do ensaio; o acumulado ajuda a saber se está adiantado ou atrasado.

## 1. Capa · 20 s (acumulado 0:20)

Meu trabalho é um sistema de transmissão digital completo: eu digito um texto, ele vira bits, passa por um canal com ruído e é reconstruído do outro lado. No caminho, comparo duas modulações e dois códigos de linha e meço quantos bits chegam errados.

## 2. A cadeia · 60 s (acumulado 1:20)

Esta é a cadeia inteira, e cada caixa é um arquivo Python. Em cima, o transmissor: a mensagem em ASCII vira bits; o código de linha transforma os bits em chips, que é o que de fato vai para o meio; e a modulação transforma os chips em símbolos. O canal soma ruído gaussiano, o AWGN, com nível controlado. Embaixo, o receptor faz o caminho de volta: demodula, decodifica e junta os bits em texto. No fim, comparo o que chegou com o que foi enviado para calcular a BER, a taxa de erro de bits. Um detalhe de implementação: a simulação é em banda base, cada símbolo é um número complexo, I mais jQ, sem gerar a senoide da portadora. Isso não muda a BER e permite simular milhões de bits em segundos.

## 3. Bits viram chips · 60 s (acumulado 2:20)

Começando pela fonte: cada caractere vira 8 bits. O R, primeira letra da mensagem de teste, é 82 em ASCII, ou 0 1 0 1 0 0 1 0. Depois vem o código de linha. No NRZ, cada bit vira um chip igual a ele: é a referência. No Manchester, cada bit vira dois chips: o 0 vira 1 0, uma descida no meio do bit, e o 1 vira 0 1, uma subida. É a convenção da Ethernet de 10 megabits. Reparem que a linha do Manchester tem o dobro de chips: isso vai custar o dobro de banda. No receptor, o Manchester não decide chip por chip: ele compara as duas metades do bit; se a segunda for maior, é uma subida, bit 1. Assim aproveita a energia dos dois chips.

## 4. Modulações · 70 s (acumulado 3:30)

Duas modulações. No BPSK, cada chip vira um símbolo: o 0 é menos 1, o 1 é mais 1, ou seja, fases de 180 e 0 graus. Na 16-QAM, quatro chips viram um símbolo: os dois primeiros escolhem a posição no eixo I, o horizontal, e os dois últimos no eixo Q, o vertical. São 16 pontos, e cada um carrega 4 bits. Os rótulos seguem o código de Gray: dois pontos vizinhos diferem em um único chip. Como o erro mais comum é o ruído empurrar o símbolo para o vizinho, esse erro custa 1 chip, e não 2. A grade é dividida por raiz de 10 para que a energia média seja 1, igual à do BPSK: as duas modulações transmitem com a mesma potência. E o demodulador não devolve só 0 ou 1: devolve um número por chip, em que o sinal diz o valor e o tamanho diz a confiança. É esse número que o Manchester usa para comparar as duas metades do bit.

## 5. Canal e SNR · 50 s (acumulado 4:20)

O canal. A SNR é a energia de um símbolo sobre o ruído. Só que os esquemas carregam números diferentes de bits por símbolo, de meio bit até 4. Para comparar de forma justa, eu fixo o Eb/N0, a energia por bit de informação, e converto para SNR com esta fórmula. Na tabela: o BPSK com NRZ tem 1 bit por símbolo, então SNR e Eb/N0 são iguais; a 16-QAM com NRZ tem 4, e a SNR fica 6 dB acima; o BPSK com Manchester tem meio bit por símbolo, e fica 3 abaixo. Como a energia do símbolo é 1, o nível de ruído sai direto da SNR. E eu conferi o ruído gerado: pedi 10 dB e medi 10,001.

## 6. Validação · 45 s (acumulado 5:05)

Antes de medir qualquer coisa, eu conferi. O validar.py roda 27 verificações, de cada bloco isolado até a cadeia inteira. Sem ruído, a BER tem que dar zero, e deu nos 4 esquemas. Depois, cada ponto das curvas transmite blocos de um milhão de bits até juntar 200 erros, o que dá uma incerteza de uns 14 por cento. Abaixo de 10 a menos 7 eu não simulo, porque seriam bilhões de bits. E a semente é fixa: qualquer pessoa roda o experimentos.py e obtém exatamente estes números, em uns 25 segundos.

## 7. BER × Eb/N0 · 70 s (acumulado 6:15)

O resultado principal. No eixo horizontal, o Eb/N0; no vertical, a BER em escala logarítmica: cada linha de grade é 10 vezes menos erro. As linhas são a teoria, os marcadores a simulação, e eles coincidem nos 4 esquemas. A referência usual é BER de 10 a menos 5, um bit errado a cada cem mil. O BPSK chega lá com 9,59 dB, com NRZ ou com Manchester: as duas curvas são a mesma. A 16-QAM com NRZ precisa de 13,43, quase 4 dB a mais. E a 16-QAM com Manchester fica no meio, com 10,56, um resultado que eu explico daqui a pouco.

## 8. BER × SNR · 50 s (acumulado 7:05)

O enunciado pede a BER em função da SNR, então aqui está o mesmo resultado com a SNR no eixo. As curvas se deslocam e a ordem muda: agora o BPSK com Manchester parece o melhor, 3 dB à frente do NRZ. Mas é efeito do eixo: cada bit Manchester ocupa dois símbolos, então, com a mesma energia por símbolo, cada bit recebe o dobro de energia, pagando com o dobro do tempo e da banda. Por isso a comparação entre esquemas eu fiz em Eb/N0.

## 9. Mensagem de teste · 50 s (acumulado 7:55)

O que isso significa para quem lê a mensagem. Transmiti "Redes de Computadores - UNISINOS 2026", 296 bits, nos 4 esquemas. Em laranja estão os caracteres que chegaram errados. A 2 dB, nenhum esquema dá conta: o texto fica ilegível. A 6 dB, o BPSK já entrega quase tudo, e a 16-QAM com NRZ ainda erra 9 bits. A 10 dB, os 4 chegam intactos. E os números batem com a teoria: para a 16-QAM a 6 dB, a BER prevista dava uns 8 bits errados em 296, e foram 9.

## 10. BPSK × 16-QAM · 60 s (acumulado 8:55)

Primeira comparação pedida: as modulações, com o mesmo código, o NRZ. A 16-QAM precisa de 3,85 dB a mais que o BPSK, mas transmite 4 vezes mais bits no mesmo Hz de banda. O porquê está na constelação: com a mesma energia média, os 16 pontos ficam muito mais apertados, a 0,63 um do outro, contra 2 no BPSK. Então basta menos ruído para confundir um símbolo com o vizinho. É a troca entre potência e banda. O BPSK serve onde a potência é pouca e a banda sobra, como em satélites. A 16-QAM, onde o sinal é bom e a banda é cara: Wi-Fi, 4G e 5G trocam de modulação conforme a qualidade do sinal.

## 11. NRZ × Manchester · 60 s (acumulado 9:55)

Segunda comparação: o código de linha. No BPSK, o Manchester não muda a BER em Eb/N0: 9,59 dB nos dois. Os dois chips de cada bit têm sinais opostos, e comparar os dois é o mesmo que receber um único símbolo com a energia somada. O que muda é a banda: o dobro de chips, metade da eficiência. Então o que o Manchester compra? Coisas que a BER deste simulador não mede, porque ele supõe relógio perfeito: a transição em todo bit, que deixa o receptor recuperar o relógio; o nível médio zero; e a detecção, porque os pares 0 0 e 1 1 não existem e denunciam ruído. Mas é só um alarme: a 2 dB, foram 41 pares inválidos para 5 bits errados. Ele não corrige nada; para isso seria preciso um código corretor de erros.

## 12. 16-QAM + Manchester · 70 s (acumulado 11:05)

Este foi o resultado que eu não previ. Na 16-QAM com Manchester, os dois chips de um bit caem sempre no mesmo eixo. Como o Manchester só produz 0 1 e 1 0, só aparecem os níveis menos 1 e mais 3, e a constelação de 16 pontos encolhe para 4, como se vê à direita. Vira um esquema de 2 bits por símbolo, com 10,56 dB. E por que ele perde quase 1 dB para o BPSK? Olhem o centro dos 4 pontos: não está na origem. 20 por cento da energia de cada símbolo vai nesse deslocamento, que não carrega informação. 10 log de 1 sobre 0,8 dá 0,97 dB, exatamente a diferença. Uma QPSK teria os mesmos 2 bits por símbolo sem esse desperdício. A lição é que código de linha e modulação têm que ser escolhidos juntos.

## 13. Impacto da BER · 45 s (acumulado 11:50)

O impacto da BER. Um caractere tem 8 bits e se perde se qualquer um errar. Com BER de 10 a menos 2, um caractere a cada 13 chega errado: é a mensagem ilegível de 2 dB. Com 10 a menos 5, um a cada 12.500. Parece ótimo, mas um pacote Ethernet de 1.500 bytes tem 12 mil bits: com essa mesma BER, 11 por cento dos pacotes chegariam corrompidos e teriam que ser retransmitidos. Por isso enlaces reais usam CRC para detectar erros e códigos corretores para consertá-los, além da modulação.

## 14. Eficiência e Shannon · 50 s (acumulado 12:40)

E a eficiência. No eixo vertical, quantos bits por segundo cada Hz de banda carrega; no horizontal, o Eb/N0 que cada esquema precisa. A linha tracejada é o limite de Shannon: à esquerda dela, nenhum sistema funciona sem erro. Todos os meus esquemas ficam entre 7,7 e 10,4 dB longe do limite, porque nenhum usa código corretor. O mais próximo é a 16-QAM com NRZ: modulações de ordem alta aproveitam melhor um canal bom. O mais distante é o BPSK com Manchester: gasta a mesma energia que o NRZ e entrega metade da eficiência.

## 15. Método e IA · 40 s (acumulado 13:20)

Sobre o método. Usei IA, o Claude Code, no planejamento, no código e nos textos, sempre com uma previsão antes de rodar. Duas previsões foram corrigidas pelos testes: as quatro combinações não eram todas limpas, porque a 16-QAM com Manchester usava só 4 pontos; e a contagem de pares inválidos não mede erros. Todo número foi conferido contra a teoria e pelo validar.py, e a execução oficial é minha, com semente fixa.

## 16. Conclusão · 45 s (acumulado 14:05)

Para fechar. A modulação troca potência por banda: a 16-QAM dá 4 vezes os bits por Hz por 3,85 dB a mais. O código de linha troca banda por propriedades do sinal: o Manchester não muda a BER e dobra a banda, em troca de sincronismo. Então a escolha depende do enlace: com pouca potência, BPSK com NRZ; com banda escassa e sinal bom, 16-QAM; se o receptor precisa tirar o relógio do próprio sinal, Manchester. E em todos os casos, simulação e teoria bateram.

## 17. Perguntas · 10 s (acumulado 14:15)

Obrigado. O código, o relatório e os resultados estão no GitHub, e o README explica como rodar. Se houver tempo, mostro ao vivo uma transmissão com o sistema.py.
