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

volatile float currentTemperature = 0.0f;
volatile uint16_t rawAdc = 0;

static void SystemClock_Init(void);
static void GPIO_Init(void);
static void ADC_Init(void);
static void I2C1_Init(void);
static uint16_t ADC_Read(void);
static void delay_cycles(volatile uint32_t count);
static uint8_t I2C1_WriteData(uint16_t memAddr, const uint8_t *pData, uint16_t size);
static void ST25DV_WriteCompactNDEF(float temp);

int main(void)
{
    SystemClock_Init();
    GPIO_Init();
    ADC_Init();
    I2C1_Init();

    delay_cycles(10000);

    while (1)
    {
        // 1. أخذ قراءة الـ ADC
        rawAdc = ADC_Read();
        if (rawAdc == 0) rawAdc = 1;

        // 2. حساب درجة الحرارة
        float resistance = SERIES_RESISTOR * ((4095.0f / (float)rawAdc) - 1.0f);
        float steinhart = resistance / NOMINAL_RESISTANCE;
        steinhart = logf(steinhart);
        steinhart /= B_COEFFICIENT;
        steinhart += 1.0f / (NOMINAL_TEMPERATURE + 273.15f);
        steinhart = 1.0f / steinhart;
        currentTemperature = steinhart - 273.15f;

        // 3. كتابة القراءة في الـ NFC مع إعادة المحاولة التلقائية
        ST25DV_WriteCompactNDEF(currentTemperature);

        // تأخير خفيف قبل التحديث التالي
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
    while (!(RCC_CR & (1U << 2))); // الانتظار الصحيح على MSIRDY (Bit 2)

    RCC_ICSCR &= ~(7U << 13);
    RCC_ICSCR |=  (5U << 13);      // التردد 2.097 MHz

    RCC_CFGR &= ~3U;
    while ((RCC_CFGR & (3U << 2)) != 0);
}

static void GPIO_Init(void)
{
    RCC_IOPENR |= (1U << 0);

    GPIOA_MODER |= (3U << (0 * 2)); // PA0 Analog

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

    ADC1_CHSELR = (1U << 0);
    ADC1_SMPR |= 0x07;
}

static uint16_t ADC_Read(void)
{
    uint32_t timeout = 50000;
    ADC1_CR |= (1U << 2);
    while (!(ADC1_ISR & (1U << 2)))
    {
        if (--timeout == 0) return 2048;
    }
    return (uint16_t)ADC1_DR;
}

static void I2C1_Init(void)
{
    RCC_APB1ENR |= (1U << 21);
    I2C1_CR1 &= ~(1U << 0);
    I2C1_TIMINGR = 0x00000509; // 100kHz
    I2C1_CR1 |= (1U << 0);
}

/* دالة الكتابة مع معالجة حماية الـ RF Busy والـ NACK */
static uint8_t I2C1_WriteData(uint16_t memAddr, const uint8_t *pData, uint16_t size)
{
    uint32_t totalBytes = size + 2;
    uint32_t timeout;
    uint8_t retries = 15;

    while (retries--)
    {
        I2C1_ICR = (1U << 4) | (1U << 5); // مسح أعلام الأخطاء السابقة

        I2C1_CR2 = ((uint32_t)(ST25DV_ADDR_DATA << 1)) | (totalBytes << 16) | (1U << 25);
        I2C1_CR2 |= (1U << 13); // إرسال START

        timeout = 30000;
        while (!(I2C1_ISR & (1U << 1)))
        {
            if (I2C1_ISR & (1U << 4)) goto retry; // إذا أعطت الشريحة NACK بسبب انشغال الـ RF أعد المحاولة
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

        delay_cycles(15000); // مهلة تثبيت الـ EEPROM داخلياً
        return 0; // نجحت الكتابة

    retry:
        I2C1_CR2 |= (1U << 14); // توليد STOP لتحرير الخط
        delay_cycles(4000);
    }

    return 1;
}

static void ST25DV_WriteCompactNDEF(float temp)
{
    char textPayload[16];
    int intPart = (int)temp;
    int fracPart = (int)((temp - intPart) * 10);
    if (fracPart < 0) fracPart = -fracPart;

    snprintf(textPayload, sizeof(textPayload), "%d.%d C", intPart, fracPart);
    uint8_t payloadLen = (uint8_t)strlen(textPayload);

    uint8_t ndefBuffer[32];
    uint8_t idx = 0;

    ndefBuffer[idx++] = 0xE1;
    ndefBuffer[idx++] = 0x40;
    ndefBuffer[idx++] = 0x08;
    ndefBuffer[idx++] = 0x01;

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
