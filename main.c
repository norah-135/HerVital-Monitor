#include <stdint.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* --- عناوين السجلات الأساسية --- */
#define PERIPH_BASE           (0x40000000UL)
#define APB1PERIPH_BASE       (PERIPH_BASE)
#define APB2PERIPH_BASE       (PERIPH_BASE + 0x00010000UL)
#define AHBPERIPH_BASE        (PERIPH_BASE + 0x00020000UL)
#define IOPORT_BASE           (PERIPH_BASE + 0x10000000UL)

/* RCC */
#define RCC_BASE              (AHBPERIPH_BASE + 0x1000UL)
#define RCC_CR                (*(volatile uint32_t *)(RCC_BASE + 0x00))
#define RCC_ICSCR             (*(volatile uint32_t *)(RCC_BASE + 0x04))
#define RCC_CFGR              (*(volatile uint32_t *)(RCC_BASE + 0x0C))
#define RCC_IOPENR            (*(volatile uint32_t *)(RCC_BASE + 0x2C))
#define RCC_APB1ENR           (*(volatile uint32_t *)(RCC_BASE + 0x38))
#define RCC_APB2ENR           (*(volatile uint32_t *)(RCC_BASE + 0x34))

/* GPIOA */
#define GPIOA_BASE            (IOPORT_BASE + 0x0000UL)
#define GPIOA_MODER           (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_OTYPER          (*(volatile uint32_t *)(GPIOA_BASE + 0x04))
#define GPIOA_OSPEEDR         (*(volatile uint32_t *)(GPIOA_BASE + 0x08))
#define GPIOA_PUPDR           (*(volatile uint32_t *)(GPIOA_BASE + 0x0C))
#define GPIOA_AFRH            (*(volatile uint32_t *)(GPIOA_BASE + 0x24))

/* ADC1 */
#define ADC1_BASE             (APB2PERIPH_BASE + 0x2400UL)
#define ADC1_ISR              (*(volatile uint32_t *)(ADC1_BASE + 0x00))
#define ADC1_CR               (*(volatile uint32_t *)(ADC1_BASE + 0x08))
#define ADC1_SMPR             (*(volatile uint32_t *)(ADC1_BASE + 0x14))
#define ADC1_CHSELR           (*(volatile uint32_t *)(ADC1_BASE + 0x28))
#define ADC1_DR               (*(volatile uint32_t *)(ADC1_BASE + 0x40))

/* I2C1 */
#define I2C1_BASE             (APB1PERIPH_BASE + 0x5400UL)
#define I2C1_CR1              (*(volatile uint32_t *)(I2C1_BASE + 0x00))
#define I2C1_CR2              (*(volatile uint32_t *)(I2C1_BASE + 0x04))
#define I2C1_TIMINGR          (*(volatile uint32_t *)(I2C1_BASE + 0x10))
#define I2C1_ISR              (*(volatile uint32_t *)(I2C1_BASE + 0x18))
#define I2C1_ICR              (*(volatile uint32_t *)(I2C1_BASE + 0x1C))
#define I2C1_TXDR             (*(volatile uint32_t *)(I2C1_BASE + 0x28))

/* ثوابت الحساس */
#define SERIES_RESISTOR       100000.0f
#define NOMINAL_RESISTANCE    100000.0f
#define NOMINAL_TEMPERATURE   25.0f
#define B_COEFFICIENT         3950.0f

#define ST25DV_ADDR_DATA      0x53

volatile float temp_sensor1 = 0.0f;
volatile float temp_sensor2 = 0.0f;
volatile uint16_t rawAdc1 = 0;
volatile uint16_t rawAdc2 = 0;

static void SystemClock_Init(void);
static void GPIO_Init(void);
static void ADC_Init(void);
static void I2C1_Init(void);
static uint16_t ADC_ReadChannel(uint32_t channel);
static float CalculateTemperature(uint16_t adc_val);
static void delay_cycles(volatile uint32_t count);
static uint8_t I2C1_WriteData(uint16_t memAddr, const uint8_t *pData, uint16_t size);
static void ST25DV_WriteDualNDEF(float t1, float t2);

int main(void)
{
    SystemClock_Init();
    GPIO_Init();
    ADC_Init();
    I2C1_Init();

    delay_cycles(10000);

    while (1)
    {
        // 1. قراءة الحساس الأول (PA0 -> Channel 0)
        rawAdc1 = ADC_ReadChannel(0);
        temp_sensor1 = CalculateTemperature(rawAdc1);

        // 2. قراءة الحساس الثاني (PA1 -> Channel 1)
        rawAdc2 = ADC_ReadChannel(1);
        temp_sensor2 = CalculateTemperature(rawAdc2);

        // 3. كتابة القراءتين معاً في الـ NFC
        ST25DV_WriteDualNDEF(temp_sensor1, temp_sensor2);

        delay_cycles(80000);
    }
}

static void delay_cycles(volatile uint32_t count)
{
    while (count--) { __asm("nop"); }
}

static void SystemClock_Init(void)
{
    RCC_CR |= (1U << 0);
    while (!(RCC_CR & (1U << 2))); // الانتظار على MSIRDY (Bit 2)

    RCC_ICSCR &= ~(7U << 13);
    RCC_ICSCR |=  (5U << 13);      // 2.097 MHz

    RCC_CFGR &= ~3U;
    while ((RCC_CFGR & (3U << 2)) != 0);
}

static void GPIO_Init(void)
{
    RCC_IOPENR |= (1U << 0);

    // ضبط PA0 و PA1 كمدخلات تناظرية (Analog Mode: 11)
    GPIOA_MODER |= (3U << (0 * 2)) | (3U << (1 * 2));

    // PA9 (SCL) و PA10 (SDA) للـ I2C
    GPIOA_MODER &= ~((3U << (9 * 2)) | (3U << (10 * 2)));
    GPIOA_MODER |=  ((2U << (9 * 2)) | (2U << (10 * 2)));

    GPIOA_OTYPER |= (1U << 9) | (1U << 10);
    GPIOA_OSPEEDR &= ~((3U << (9 * 2)) | (3U << (10 * 2)));

    GPIOA_PUPDR &= ~((3U << (9 * 2)) | (3U << (10 * 2)));
    GPIOA_PUPDR |=  ((1U << (9 * 2)) | (1U << (10 * 2)));

    GPIOA_AFRH &= ~((0xFU << ((9 - 8) * 4)) | (0xFU << ((10 - 8) * 4)));
    GPIOA_AFRH |=  ((1U << ((9 - 8) * 4)) | (1U << ((10 - 8) * 4)));
}

static void ADC_Init(void)
{
    RCC_APB2ENR |= (1U << 9);

    if (ADC1_CR & (1U << 0)) ADC1_CR |= (1U << 1);
    while (ADC1_CR & (1U << 0));
    ADC1_CR |= (1U << 31);
    while (ADC1_CR & (1U << 31));

    ADC1_ISR |= (1U << 0);
    ADC1_CR |= (1U << 0);
    while (!(ADC1_ISR & (1U << 0)));

    ADC1_SMPR |= 0x07;
}

static uint16_t ADC_ReadChannel(uint32_t channel)
{
    uint32_t timeout = 50000;

    // اختيار القناة المطلوبة
    ADC1_CHSELR = (1U << channel);

    ADC1_CR |= (1U << 2); // بدء التحويل
    while (!(ADC1_ISR & (1U << 2)))
    {
        if (--timeout == 0) return 2048;
    }
    return (uint16_t)ADC1_DR;
}

static float CalculateTemperature(uint16_t adc_val)
{
    if (adc_val == 0) adc_val = 1;
    float resistance = SERIES_RESISTOR * ((4095.0f / (float)adc_val) - 1.0f);
    float steinhart = resistance / NOMINAL_RESISTANCE;
    steinhart = logf(steinhart);
    steinhart /= B_COEFFICIENT;
    steinhart += 1.0f / (NOMINAL_TEMPERATURE + 273.15f);
    steinhart = 1.0f / steinhart;
    return (steinhart - 273.15f);
}

static void I2C1_Init(void)
{
    RCC_APB1ENR |= (1U << 21);
    I2C1_CR1 &= ~(1U << 0);
    I2C1_TIMINGR = 0x00000509; // 100kHz
    I2C1_CR1 |= (1U << 0);
}

static uint8_t I2C1_WriteData(uint16_t memAddr, const uint8_t *pData, uint16_t size)
{
    uint32_t totalBytes = size + 2;
    uint32_t timeout;
    uint8_t retries = 15;

    while (retries--)
    {
        I2C1_ICR = (1U << 4) | (1U << 5);

        I2C1_CR2 = ((uint32_t)(ST25DV_ADDR_DATA << 1)) | (totalBytes << 16) | (1U << 25);
        I2C1_CR2 |= (1U << 13);

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 1)))
        {
            if (I2C1_ISR & (1U << 4)) goto retry;
            if (--timeout == 0) goto retry;
        }
        I2C1_TXDR = (memAddr >> 8) & 0xFF;

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 1)))
        {
            if (I2C1_ISR & (1U << 4)) goto retry;
            if (--timeout == 0) goto retry;
        }
        I2C1_TXDR = memAddr & 0xFF;

        for (uint16_t i = 0; i < size; i++)
        {
            timeout = 30000;
            while (!(I2C1_ISR & (1U << 1)))
            {
                if (I2C1_ISR & (1U << 4)) goto retry;
                if (--timeout == 0) goto retry;
            }
            I2C1_TXDR = pData[i];
        }

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 5))) { if (--timeout == 0) break; }
        I2C1_ICR = (1U << 5);

        delay_cycles(15000);
        return 0;

    retry:
        I2C1_CR2 |= (1U << 14);
        delay_cycles(4000);
    }

    return 1;
}

static void ST25DV_WriteDualNDEF(float t1, float t2)
{
    char textPayload[64]; // تكبير الحجم لحل مشكلة format-truncation نهائياً
    int int1 = (int)t1;
    int frac1 = (int)((t1 - int1) * 10);
    if (frac1 < 0) frac1 = -frac1;

    int int2 = (int)t2;
    int frac2 = (int)((t2 - int2) * 10);
    if (frac2 < 0) frac2 = -frac2;

    // كتابة النص المدمج بأمان
    snprintf(textPayload, sizeof(textPayload), "T1:%d.%d T2:%d.%d C", int1, frac1, int2, frac2);
    uint8_t payloadLen = (uint8_t)strlen(textPayload);

    uint8_t ndefBuffer[80];
    uint8_t idx = 0;

    // CC File
    ndefBuffer[idx++] = 0xE1;
    ndefBuffer[idx++] = 0x40;
    ndefBuffer[idx++] = 0x08;
    ndefBuffer[idx++] = 0x01;

    // NDEF Text Record
    ndefBuffer[idx++] = 0x03;
    ndefBuffer[idx++] = 7 + payloadLen;
    ndefBuffer[idx++] = 0xD1;
    ndefBuffer[idx++] = 0x01;
    ndefBuffer[idx++] = 3 + payloadLen;
    ndefBuffer[idx++] = 'T';
    ndefBuffer[idx++] = 0x02;
    ndefBuffer[idx++] = 'e';
    ndefBuffer[idx++] = 'n';

    memcpy(&ndefBuffer[idx], textPayload, payloadLen);
    idx += payloadLen;

    ndefBuffer[idx++] = 0xFE;

    I2C1_WriteData(0x0000, ndefBuffer, idx);
}
