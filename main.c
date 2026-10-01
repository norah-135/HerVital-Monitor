#include <stdint.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* ====================================================================
   1. تعريفات العناوين والسجلات الأساسية (STM32L0)
   ==================================================================== */
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

/* ====================================================================
   2. ثوابت الحساس وشريحة ST25DV
   ==================================================================== */
#define SERIES_RESISTOR       100000.0f
#define NOMINAL_RESISTANCE    100000.0f
#define NOMINAL_TEMPERATURE   25.0f
#define B_COEFFICIENT         3950.0f

#define ST25DV_ADDR_DATA      0x53

volatile float temp_sensor1 = 0.0f;
volatile float temp_sensor2 = 0.0f;
volatile uint16_t rawAdc1 = 0;
volatile uint16_t rawAdc2 = 0;

/* ====================================================================
   3. الدوال البرمجية المساعدة
   ==================================================================== */
static void delay_cycles(volatile uint32_t count)
{
    while (count--) { __asm("nop"); }
}

static void SystemClock_Init(void)
{
    RCC_CR |= (1U << 0);
    while (!(RCC_CR & (1U << 2))); // الانتظار حتى استقرار MSIRDY

    RCC_ICSCR &= ~(7U << 13);
    RCC_ICSCR |=  (5U << 13);      // ضبط التردد على Range 5 (2.097 MHz) لاستهلاك طاقة منخفض

    RCC_CFGR &= ~3U;
    while ((RCC_CFGR & (3U << 2)) != 0);
}

static void GPIO_Init(void)
{
    RCC_IOPENR |= (1U << 0); // تفعيل ساعة GPIOA

    // ضبط PA0 و PA1 كمدخلات تناظرية Analog (11)
    GPIOA_MODER |= (3U << (0 * 2)) | (3U << (1 * 2));

    // ضبط PA9 (SCL) و PA10 (SDA) لوظيفة I2C1 البديلة (AF1)
    GPIOA_MODER &= ~((3U << (9 * 2)) | (3U << (10 * 2)));
    GPIOA_MODER |=  ((2U << (9 * 2)) | (2U << (10 * 2)));

    GPIOA_OTYPER |= (1U << 9) | (1U << 10); // Open Drain
    GPIOA_OSPEEDR &= ~((3U << (9 * 2)) | (3U << (10 * 2)));

    GPIOA_PUPDR &= ~((3U << (9 * 2)) | (3U << (10 * 2)));
    GPIOA_PUPDR |=  ((1U << (9 * 2)) | (1U << (10 * 2))); // Pull-up

    GPIOA_AFRH &= ~((0xFU << ((9 - 8) * 4)) | (0xFU << ((10 - 8) * 4)));
    GPIOA_AFRH |=  ((1U << ((9 - 8) * 4)) | (1U << ((10 - 8) * 4))); // AF1
}

static void ADC_Init(void)
{
    RCC_APB2ENR |= (1U << 9);

    if (ADC1_CR & (1U << 0)) ADC1_CR |= (1U << 1);
    while (ADC1_CR & (1U << 0));
    ADC1_CR |= (1U << 31); // معايرة الـ ADC
    while (ADC1_CR & (1U << 31));

    ADC1_ISR |= (1U << 0);
    ADC1_CR |= (1U << 0);  // تمكين الـ ADC
    while (!(ADC1_ISR & (1U << 0)));

    ADC1_SMPR |= 0x07;     // أطول زمن لأخذ العينة لضمان أعلى دقة
}

static uint16_t ADC_ReadChannelAvg(uint32_t channel)
{
    uint32_t sum = 0;
    ADC1_CHSELR = (1U << channel);

    // أخذ متوسط 4 عينات لتفادي أي تشويش كهربائي
    for (int i = 0; i < 4; i++)
    {
        uint32_t timeout = 25000;
        ADC1_CR |= (1U << 2); // بدء التحويل
        while (!(ADC1_ISR & (1U << 2)))
        {
            if (--timeout == 0) break;
        }
        sum += (uint16_t)ADC1_DR;
        delay_cycles(400);
    }
    return (uint16_t)(sum / 4);
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
    I2C1_TIMINGR = 0x00000509; // 100kHz Standard Mode
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
        I2C1_CR2 |= (1U << 13); // START condition

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

        delay_cycles(15000); // مهلة تثبيت كتابة الـ EEPROM داخلياً
        return 0;

    retry:
        I2C1_CR2 |= (1U << 14); // STOP condition
        delay_cycles(4000);
    }

    return 1;
}

static void ST25DV_WriteUriNDEF(float t1, float t2)
{
    char urlPayload[80];
    int int1 = (int)t1;
    int frac1 = (int)((t1 - int1) * 10);
    if (frac1 < 0) frac1 = -frac1;

    int int2 = (int)t2;
    int frac2 = (int)((t2 - int2) * 10);
    if (frac2 < 0) frac2 = -frac2;

    // استخدام قيمة ADC الحية كمعامل عشوائي لمنع الكاش وإجبار الآيفون على إظهار الإشعار دائماً
    snprintf(urlPayload, sizeof(urlPayload),
             "192.168.0.113:5000/update?t1=%d.%d&t2=%d.%d&_=%u",
             int1, frac1, int2, frac2, (unsigned int)(rawAdc1 & 0xFF));

    uint8_t urlLen = (uint8_t)strlen(urlPayload);
    uint8_t payloadLen = 1 + urlLen;
    uint8_t recordLen  = 3 + 1 + payloadLen;

    uint8_t ndefBuffer[110];
    uint8_t idx = 0;

    // 1. CC File (4 Bytes) القياسي لـ Type 5 Tag
    ndefBuffer[idx++] = 0xE1;
    ndefBuffer[idx++] = 0x40;
    ndefBuffer[idx++] = 0x08;
    ndefBuffer[idx++] = 0x01;

    // 2. NDEF Message TLV
    ndefBuffer[idx++] = 0x03;
    ndefBuffer[idx++] = recordLen;

    // 3. Record Header
    ndefBuffer[idx++] = 0xD1;
    ndefBuffer[idx++] = 0x01;
    ndefBuffer[idx++] = payloadLen;
    ndefBuffer[idx++] = 'U';

    // 4. Record Payload
    ndefBuffer[idx++] = 0x03; // اختصار بروتوكول "http://"
    memcpy(&ndefBuffer[idx], urlPayload, urlLen);
    idx += urlLen;

    // 5. Terminator TLV
    ndefBuffer[idx++] = 0xFE;

    I2C1_WriteData(0x0000, ndefBuffer, idx);
}

/* ====================================================================
   4. دالة التنفيذ الرئيسية (One-Shot Architecture)
   ==================================================================== */
int main(void)
{
    // تهيئة العتاد الداخلي
    SystemClock_Init();
    GPIO_Init();
    ADC_Init();
    I2C1_Init();

    // مهلة حاسمة لاستقرار جهد VEH وشحن مكثف التغذية من الجوال
    delay_cycles(60000);

    // 1. قراءة متوسط الحساسين لضمان قياس حقيقي ومستقر
    rawAdc1 = ADC_ReadChannelAvg(0);
    temp_sensor1 = CalculateTemperature(rawAdc1);

    rawAdc2 = ADC_ReadChannelAvg(1);
    temp_sensor2 = CalculateTemperature(rawAdc2);

    // 2. كتابة الرابط لمرة واحدة فقط وبأقصى سرعة
    ST25DV_WriteUriNDEF(temp_sensor1, temp_sensor2);

    // مهلة قصيرة لاكتمال دورة كتابة الـ EEPROM
    delay_cycles(20000);

    // 3. إيقاف منفذ I2C تماماً لتحرير الشريحة ومنع أي تعارض مع موجات RF الخاصة بالآيفون
    I2C1_CR1 &= ~(1U << 0);

    // 4. إدخال المعالج في سكون تام لخفض استهلاك الطاقة إلى الصفر
    while (1)
    {
        __asm("wfi");
    }
}
